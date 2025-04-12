from collections import defaultdict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain.agents import AgentExecutor, create_openai_tools_agent
from utils.web_search import SEARCH_TOOL_MAP
from langchain_core.tools import tool
import os

load_dotenv()

# --- Base Prompt ---
BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant to help answer the user's questions. Aim for a comprehensive answer that covers all relevant information. If the user asks a simple question, provide a simple answer. Your focus is to answer the user's question. If the user wants a more detailed answer, provide a detailed answer. And if the user wants a summary, provide a concise answer."
    r"""If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: The relationship between input variables and the output can often be expressed in a general form, such as ($Y = f(X) + \epsilon$), where ($Y$) is the response variable, ($X$) represents the input variables, ($f$) is an unknown function describing the relationship, and ($\epsilon$) is the error term.. Example: **$X_i$**: The individual data points for the variable $X$. When using block equations $$...$$, when the equation is over, use a new line to start the next text or equation. Example: General Form of the Model: The relationship between the response variable $Y$ and the predictors $X_1$, $X_2$, $\ldots$, $X_p$ can be expressed in a general form:"""
    "If the user asks for a summary, provide a concise answer."
)

# --- Agent Prompt ---
# Incorporating BASE_SYSTEM_PROMPT
AGENT_PROMPT_TEMPLATE = """
You are a highly specialized information gathering assistant. Your SOLE purpose is to use the available tools to collect information relevant to the user's query. You MUST NOT answer the user's question directly or provide any summary. Your final output should ONLY be 'Information gathering complete.' after using the necessary tools.

Available Tools: You may have access to 'retrieve' (for searching provided documents) and web search tools ('web', 'academic', 'social'). Always check which tools are available first.

CRITICAL WORKFLOW:

1.  **Analyze the Query:**
    *   Carefully read the user's entire query: {input}
    *   Break it down into genuinely distinct, non-overlapping core subjects or topics. **Group closely related concepts (e.g., 'KOOS summary' and 'KOOS additional info') under ONE primary topic if they refer to the same entity ('KOOS questionnaire').** Avoid creating separate topics for slight variations of the same core subject.
    *   Identify **Explicit External Information Requests**: Look for phrases like "além disso", "informe mais sobre", "coisas a mais que não aborda", "pesquise", "busque", "baseado na literatura", "quero saber mais". Note *exactly which primary topic* these phrases apply to.

2.  **Information Gathering Strategy & Uniqueness Rules:**

    *   **Phase 1: Document Retrieval (using 'retrieve' tool)**
        *   **Mandatory Uniqueness:** For each *primary topic* identified, you MUST use the 'retrieve' tool (if available) **AT MOST ONCE**.
        *   Formulate a concise, keyword-based query (3-5 words max) representing the *core essence* of the topic. Remove filler words and context like "no projeto".
        *   **Example Query Transformation:**
            *   User Query Part: "resumo sobre o que o projeto fala em relação ao questionário koos" -> Primary Topic: "KOOS questionnaire" -> `retrieve` Query: "questionário koos projeto"
            *   User Query Part: "critérios de rejeição de pacientes no projeto da unima" -> Primary Topic: "rejection criteria" -> `retrieve` Query: "critérios rejeição pacientes"

    *   **Phase 2: Web Search (using 'web', 'academic', or 'social' tools - CONDITIONAL)**
        *   **Trigger:** Perform this phase **ONLY** if web search tools are available **AND** you identified an **Explicit External Information Request** for a specific *primary topic* in Step 1.
        *   **Mandatory Uniqueness:** If web search is triggered for a primary topic, you MUST use all available chosen web search tool ('web', 'academic', 'social') **AT MOST ONCE** for that specific topic's external information need.
        *   Formulate a concise, keyword-based query (3-5 words max) focusing on the *additional information* requested for that topic.
        *   **Example Scenario:**
            *   User Query: "Quais são os critérios de rejeição no projeto? Além disso, me informe coisas a mais sobre sintomas osteoarticulares baseado na literatura."
            *   Primary Topic 1: "rejection criteria" -> Requires External Info: No -> Plan: `retrieve`: "critérios rejeição" (ONCE)
            *   Primary Topic 2: "osteoarticular symptoms" -> Requires External Info: Yes ("Além disso...") -> Plan: `retrieve`: "sintomas osteoarticulares" (ONCE), THEN `web`/`academic`/'social': "sintomas osteoarticulares literatura" (REPEATE FOR ALL AVAILABLE WEB SEARCHTOOLS (WEB, ACADEMIC, SOCIAL))

3.  **Execution Format & History Check:**
    *   Maintain an internal list of `(Tool Name, Core Topic Keywords)` pairs already executed in THIS run.
    *   Follow this thought process structure:
        Tools: [List available tools]
        Query Analysis:
        - Primary Topic 1: [Description] -> Requires External Info: [Yes/No]
        - Primary Topic 2: [Description] -> Requires External Info: [Yes/No]
        ... (Ensure topics are truly distinct core subjects)
        Phase 1 Plan (Retrieve - Max 1 per topic): [List actions and queries]
        Phase 2 Plan (Web Search - Max 1 per topic, only if triggered): [List actions and queries]
        --- Start Execution ---
        Action: [Tool Name]
        Action Input: [Concise Query]
        **RIGOROUS History Check:** Have I already executed ('[Tool Name]', '[Core Topic Keywords]') in this specific run? [Yes/No]
        **(IF YES, Thought: Duplicate action detected for '[Tool Name]' on topic '[Core Topic Keywords]'. SKIPPING this action. Proceeding to next planned step.)**
        **(IF NO, Thought: Executing unique action. Adding ('[Tool Name]', '[Core Topic Keywords]') to executed list.)**
        Observation: [Result Snippet (only if action was executed)]
        Thought: [Assess info gathered for this specific step, plan next action based on strategy and uniqueness rules]
        ...(Repeat Action/History Check/Observation/Thought)
    *   Once all planned and *unique* actions are complete, your ABSOLUTE FINAL output must be:
        Information gathering complete. Tools used: [list of tools used].

Previous conversation history:
{chat_history}

Begin information gathering for the new query: {input}
{agent_scratchpad}"""

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
        # Safer way to extract the title/filename
        source = metadata.get('source', '')
        if '../docs' in source:
            try:
                title = source.split("../docs")[1].strip('\\/')
            except IndexError:
                title = os.path.basename(source)
        else:
            title = metadata.get('title', os.path.basename(source))
            
        try:
            page_label = metadata.get('page_label', 'Unknown Page')
            metadata_dict[title].add(int(page_label))
        except (ValueError, TypeError):
            # If we can't convert page_label to int, just add the title to metadata_dict
            metadata_dict[title]

    # Sort the pages for each document for consistent display
    formatted_docs = []
    for title, pages in metadata_dict.items():
        if pages:  # Only add "Pages:" if there are actual page numbers
            formatted_docs.append(f"Document: {title} - Pages: {', '.join(str(p) for p in sorted(pages))}")
        else:
            formatted_docs.append(f"Document: {title}")
    
    document_info = "\n".join(formatted_docs)
    print(f"Formatted document metadata: {document_info}")
    return document_info


# --- Main Chat Function (Updated Tool Handling) ---
def chat(chat_history, vectordb, user_query, use_rag=True, use_web_search=False, search_types=None, model="gpt-4o-mini"):
    """
    Main chat function using Agentic RAG or standard LLM based on flags.
    Uses specific web search tools based on search_types.
    Uses gpt-4o-mini for the agent and the user's selected model for the final response.
    """
    if not user_query or not user_query.strip():
        return "Please provide a query.", "", []

    # Default search types if none provided and web search is enabled
    if use_web_search and (search_types is None or not search_types):
        search_types = ["web"] # Default to standard web search
        
    # Always use gpt-4o-mini for the agent operations
    agent_model = "gpt-4o-mini"
    # Use the user-selected model for final response
    response_model = model

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
    
    # Extract context from tools if they're used
    retrieved_context = ""
    web_context = ""

    # Case 1: No Tools (No RAG or Web Search) - Use the selected model directly
    if not tools:
        llm = ChatOpenAI(model=response_model, temperature=0.3, streaming=False)
        print(f"Mode: Standard LLM (No tools available or enabled) using {response_model}")
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=BASE_SYSTEM_PROMPT), # Use SystemMessage
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        chain = prompt | llm
        chat_history.append(HumanMessage(content=user_query))
        result = chain.invoke({"input": user_query, "chat_history": chat_history})
        response_content = result.content.strip()
        chat_history.append(AIMessage(content=response_content))

    # Case 2, 3, 4: Use Agent with available tools (RAG, Web Search, or both)
    else:
        # Use gpt-4o-mini for the agent operations
        agent_llm = ChatOpenAI(model=agent_model, temperature=0, streaming=False)
        print(f"Stage 1: Information gathering using {agent_model}")
        
        try:
            # Agent prompt now includes BASE_SYSTEM_PROMPT via the template
            prompt = PromptTemplate.from_template(AGENT_PROMPT_TEMPLATE)
            agent = create_openai_tools_agent(agent_llm, tools, prompt)
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                handle_parsing_errors=True,
                return_intermediate_steps=True,
                max_iterations=10,  # Prevent infinite loops
                early_stopping_method="force"  # Force stop after max_iterations
            )
            print(f"Active tool names: {active_tool_names}")
            print(f"Tools: {[t.name for t in tools]}")
            agent_input = {
                "input": user_query,
                "chat_history": chat_history,
                "available_tools": ", ".join(active_tool_names)
            }
            
            # Execute the agent to collect information using gpt-4o-mini
            agent_result = agent_executor.invoke(agent_input)
            #agent_output = agent_result['output']
            
            # Process intermediate steps to extract retrieved content
            intermediate_steps = agent_result.get("intermediate_steps", [])
            retrieved_docs_for_display = []
            web_results_for_display = []
            
            # Extract information from tool outputs
            for action, observation in intermediate_steps:
                tool_name = getattr(action, 'tool', None)
                # Process RAG tool output
                if use_rag and tool_name == rag_tool_name:
                    if isinstance(observation, list):
                        retrieved_docs_for_display = observation
                        # Collect text from retrieved documents
                        for doc in observation:
                            if hasattr(doc, 'page_content'):
                                retrieved_context += doc.page_content + "\n\n"
                    else:
                        print(f"Warning: RAG tool observation was not a list: {type(observation)}")

                # Process Web Search tool output
                if use_web_search and tool_name in SEARCH_TOOL_MAP:
                    if isinstance(observation, list):
                        web_results_for_display.extend(observation)
                        # Collect text from web results
                        for result in observation:
                            if isinstance(result, dict) and 'content' in result:
                                web_context += result['content'] + "\n\n"
                    else:
                        print(f"Warning: Web Search tool observation was not a list: {type(observation)}")

            # Format source information for display
            if use_rag:
                document_metadata = format_document_metadata_for_display(retrieved_docs_for_display)
            if use_web_search:
                web_source_info = format_web_results_for_display(web_results_for_display)
                
            # Now use the user's selected model to generate the final response
            # with the information collected by the agent
            response_llm = ChatOpenAI(model=response_model, temperature=0, streaming=False)
            print(f"Stage 2: Generating final response using {response_model}")
            
            # Prepare context from agent's findings
            final_context = "Information found from documents and web searches:\n\n"
            if retrieved_context:
                final_context += "From documents:\n" + retrieved_context + "\n\n"
            if web_context:
                final_context += "From web searches:\n" + web_context + "\n\n"
                
            # Extract the agent's reasoning from the output
            #agent_reasoning = agent_output.split("Final Answer:")[0].strip()
            
            # Use a simpler approach by creating the message directly
            full_prompt = BASE_SYSTEM_PROMPT + "\n\nI'll provide you with information collected on the topic. Create a comprehensive response based on this information to answer the user's query."

            # Create a prompt template with chat history placeholder
            response_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=full_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "Based on the following information, answer my question: {user_query}\n\nContext from sources:\n{context}")
            ])

            # Create the chain with the response model
            response_chain = response_prompt | response_llm

            # Invoke with all parameters
            final_response = response_chain.invoke({
                "chat_history": chat_history,
                "user_query": user_query,
                "context": final_context
            })

            response_content = final_response.content.strip()
            
            # Add to chat history
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=response_content))
            
        except Exception as e:
            print(f"Error during agent execution: {e}")
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc()
            response_content = f"Sorry, an error occurred while processing your request: {str(e)[:100]}..."
            # Add history for error case
            chat_history.append(HumanMessage(content=user_query))
            chat_history.append(AIMessage(content=response_content))

    return response_content, document_metadata, web_source_info