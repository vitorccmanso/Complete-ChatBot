from collections import defaultdict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from utils.web_search import SEARCH_TOOL_MAP
from langchain_core.tools import tool

load_dotenv()

# --- Base Prompt ---
BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant. You will have to answer to user's queries and ALWAYS give the most complete or longest answer possible to be sure that the user's query was properly answered."
    "You will give the most complete or longest answer possible unless the user specifies that they want a summary or a short answer."
    r"""If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: The relationship between input variables and the output can often be expressed in a general form, such as ($Y = f(X) + \epsilon$), where ($Y$) is the response variable, ($X$) represents the input variables, ($f$) is an unknown function describing the relationship, and ($\epsilon$) is the error term.. Example: **$X_i$**: The individual data points for the variable $X$. When using block equations $$...$$, when the equation is over, use a new line to start the next text or equation. Example: General Form of the Model: The relationship between the response variable $Y$ and the predictors $X_1$, $X_2$, $\ldots$, $X_p$ can be expressed in a general form:"""
    "If the user asks for a summary, provide a concise answer."
)

# --- Agent Prompt ---
# Incorporating BASE_SYSTEM_PROMPT
AGENT_PROMPT_TEMPLATE = BASE_SYSTEM_PROMPT + """

You have access to tools to help you answer the user's question. Use them when necessary.

IMPORTANT INSTRUCTIONS ABOUT SEARCH TOOLS:
1. If web search tools are available to you, YOU MUST USE THEM for any factual information, current events, or specific data, regardless of what you might already know.
2. When web search is enabled, it is MANDATORY to use it at least once for every query, even if you think you know the answer.
3. Do not rely on your own knowledge for ANY part of the question - always verify with web search when it's available.
5. If multiple search tool types (web, academic, social) are available, choose the most appropriate one(s) based on the question type.
   - Use 'web' for general information and current events
   - Use 'academic' for scholarly/scientific/technical information
   - Use 'social' for opinions, discussions, or recent posts about topics
6. The user has specifically enabled these search tools because they want fresh information from the internet, so YOU MUST use them.
7. Failure to use the web search tool when it's available is considered incorrect behavior.

Use the following format for your thought process and actions:

Question: the input question you must answer
Thought: You should always think step-by-step about how to answer the question using the available tools. Analyze the question and decide if a tool is needed. If so, choose the best tool for the task.
Action: the action to take, should be one of the available tools provided to you.
Action Input: the input required by the chosen action/tool (usually the search query or specific parameters)
Observation: the result returned by the action/tool
... (this Thought/Action/Action Input/Observation sequence can repeat multiple times if needed)
Thought: I have gathered enough information from my thoughts and tool usage. I can now formulate the final answer based on the question, chat history, and observations.
Final Answer: Provide the final, comprehensive answer to the user's original question, incorporating information from tools and citing sources as instructed. Ensure the answer directly addresses the user's query.

Begin!

Previous conversation history:
{chat_history}

New question: {input}
{agent_scratchpad}""" # agent_scratchpad is where the agent's Thoughts/Actions/Observations go

# --- Helper Functions (Keep format_web_results_for_display and format_document_metadata_for_display from previous response) ---
# Make sure format_web_results_for_display can handle the list of dicts from perform_tavily_search
def format_web_results_for_display(web_results):
    """Formats Tavily results (list of dicts) for display."""
    sources = []
    if not web_results or not isinstance(web_results, list):
        return sources

    for result in web_results:
        if isinstance(result, dict) and 'url' in result and 'title' in result:
            sources.append({
                "title": result.get("title", "N/A"),
                "url": result.get("url", "#"),
            })
        else:
             print(f"Skipping invalid item during web result formatting: {result}")

    print(f"Formatted {len(sources)} web sources for display.")
    return sources

def format_document_metadata_for_display(retrieved_docs):
    """Formats retrieved document metadata for displaying to the user."""
    if not retrieved_docs:
        return ""

    document_info = ""
    metadata_dict = defaultdict(set)
    for metadata in [doc.metadata for doc in retrieved_docs]:
        title = metadata.get('title', metadata.get('source', '').split("../docs")[1])
        page_label = metadata.get('page_label', 'Unknown Page')
        metadata_dict[title].add(int(page_label))

    # Sort the pages for each document for consistent display
    document_info = "\n".join([f"Document: {title} - Pages: {', '.join(str(p) for p in sorted(pages))}" for title, pages in metadata_dict.items()])

    print(f"Formatted document metadata: {document_info}")
    return document_info


# --- Main Chat Function (Updated Tool Handling) ---
def chat(chat_history, vectordb, user_query, use_rag=True, use_web_search=False, search_types=None):
    """
    Main chat function using Agentic RAG or standard LLM based on flags.
    Uses specific web search tools based on search_types.
    """
    if not user_query or not user_query.strip():
        return "Please provide a query.", "", []

    # Default search types if none provided and web search is enabled
    if use_web_search and (search_types is None or not search_types):
        search_types = ["web"] # Default to standard web search

    # --- Tool Setup ---
    tools = []
    active_tool_names = set() # Keep track of names for source extraction

    # RAG Tool (Conditional)
    if use_rag and vectordb:
        print("Setting up RAG tool...")
        try:
            @tool(response_format= "content")
            def retrieve(user_query):
                """
                Searches and returns relevant document excerpts and their metadata from the uploaded files.

                Use this tool when the user asks questions specifically about the information
                contained in the uploaded documents or files. The input should be the user's question.
                This tool returns both the text content and the source metadata (like filename and page).
                """
                retriever = vectordb.as_retriever()
                retrieved_docs = retriever.invoke(user_query)
                return retrieved_docs
            
            # Use a consistent name for the RAG tool
            rag_tool_name = "retrieve"
            tools.append(retrieve)
            active_tool_names.add(rag_tool_name)
            print("RAG tool created.")
        except Exception as e:
            print(f"Error creating RAG tool: {e}. Proceeding without RAG tool.")
            use_rag = False
    elif use_rag and not vectordb:
        print("Warning: RAG requested but no VectorDB provided. Disabling RAG.")
        use_rag = False

    # Web Search Tools (Conditional based on search_types)
    if use_web_search and search_types:
        print(f"Setting up Web Search tools for types: {search_types}...")
        for s_type in search_types:
            print(search_types)
            s_type = s_type.lower().strip() # Normalize type string
            if s_type in SEARCH_TOOL_MAP:
                tool_instance = SEARCH_TOOL_MAP[s_type]
                tools.append(tool_instance)
                active_tool_names.add(tool_instance.name) # Add the specific tool name
                print(f"- Added tool: {tool_instance.name}")
            else:
                print(f"Warning: Unknown search type '{s_type}' requested. Skipping.")
        if not any(tool.name in active_tool_names for tool in SEARCH_TOOL_MAP.values()):
             print("Warning: Web search enabled, but no valid search types resulted in tools being added.")

    # --- Agent/LLM Execution ---
    response_content = ""
    document_metadata = ""
    web_source_info = []

    # Case 1: No Tools (No RAG or Web Search)
    if not tools:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, streaming=False)
        print("Mode: Standard LLM (No tools available or enabled)")
        # Add BASE_SYSTEM_PROMPT here for the simple chain too
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=BASE_SYSTEM_PROMPT), # Use SystemMessage
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        chain = prompt | llm
        chat_history.append(HumanMessage(content=user_query))
        result = chain.invoke({"input": user_query, "chat_history": chat_history})
        response_content = result['output'].split("Final Answer:")[-1].strip()
        chat_history.append(AIMessage(content=response_content))

    # Case 2, 3, 4: Use Agent with available tools (RAG, Web Search, or both)
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=False)
        print(f"Mode: Agent with tools: {active_tool_names}")
        try:
            # Agent prompt now includes BASE_SYSTEM_PROMPT via the template
            prompt = PromptTemplate.from_template(AGENT_PROMPT_TEMPLATE)
            agent = create_openai_tools_agent(llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )

            agent_input = {
                "input": user_query,
                "chat_history": chat_history
            }
            result = agent_executor.invoke(agent_input)
            response_content = result['output'].split("Final Answer:")[-1].strip()

            # --- Extract Source Information ---
            intermediate_steps = result.get("intermediate_steps", [])
            retrieved_docs_for_display = []
            web_results_for_display = []

            for action, observation in intermediate_steps:
                tool_name = getattr(action, 'tool', None)
                # Process RAG tool output
                if use_rag and tool_name == rag_tool_name:
                    if isinstance(observation, list):
                        retrieved_docs_for_display = observation
                    else:
                         print(f"Warning: RAG tool observation was not a list: {type(observation)}")

                # Process Web Search tool output
                if use_web_search and tool_name in SEARCH_TOOL_MAP:
                    if isinstance(observation, list):
                        web_results_for_display.extend(observation)
                    else:
                         print(f"Warning: Web Search tool '{tool_name}' observation was not a list or string: {type(observation)}")

            print(f"Documents to format count: {len(retrieved_docs_for_display)}")
            print(f"Web results to format count: {len(web_results_for_display)}")
            # Format extracted sources
            if use_rag:
                document_metadata = format_document_metadata_for_display(retrieved_docs_for_display)
            if use_web_search:
                web_source_info = format_web_results_for_display(web_results_for_display)

            # Add history *after* agent call
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=response_content))

        except Exception as e:
            print(f"Error during agent execution: {e}")
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc()
            response_content = f"Sorry, an error occurred while processing your request with the agent: {str(e)[:100]}..."
            # Add history for error case
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=response_content))

    print(f"Document Info: {document_metadata}")
    print(f"Web Sources: {web_source_info}")
    print("--- Chat Complete ---")

    return response_content, document_metadata, web_source_info