from collections import defaultdict
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from utils.web_search import SEARCH_TOOL_MAP
from langchain_core.tools import tool
import os
import ast

load_dotenv()

# --- Base Prompt ---
BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant who provides appropriately structured responses based on question complexity. You will always answer in a markdown format. Follow these guidelines:\n"

    "## DIRECT ANSWERS FOR SIMPLE QUESTIONS (MOST IMPORTANT RULE):\n"
    "- For simple, factual, or direct questions, provide ONLY a brief, straightforward answer without any special formatting.\n"
    "- Examples of simple questions requiring ONLY direct answers:\n"
    "  * 'What's the title of the project?'\n"
    "  * 'When was the project started?'\n"
    "  * 'Who is responsible for X component?'\n"
    "  * 'How many participants were in the study?'\n"
    "  * Any yes/no questions\n"
    "  * Any question asking for a specific fact, name, date, or number\n"
    "In these cases, DO NOT use headings, sections. Simply answer the question directly.\n"
    "Only because asked a simple question, doesn't mean you can't use a basic structure to answer the question. You can and is preferred to use code blocks, bold, italic, bullet points, etc. The only requirement is that the answer is clear and easy to understand.\n"

    "## STRUCTURED FORMAT FOR COMPLEX EXPLANATIONS ONLY:\n"
    "For complex questions that require detailed explanations or analysis, you MAY use the following structure:\n"
    
    "1. A concise '# 🔍 Short Answer\n' section (1-3 sentences)\n"
    "2. A '# 📚 Deeper Dive\n' section with numbered points\n"
    "3. When needed, an '# ⚠️ Important Distinctions\n' or just the '# ⚠️' followed by the warning text, like: '⚠️ Never use eval() here' etc section\n"
    "4. A '# ✅ Conclusion\n' or '# Best Practices\n' or '# Solutions\n' or '# Recommendations\n' etc section\n"
    
    "The name of each section is option and it's completly your choosing. An answer can have none, one section or sections that are not even here, like: '# 💡 How to fix it' or '# 🚨 Possible problems' etc. It's completly up to you. The only requirement is that the sections are used to help the user understand the answer better."
    "Examples of complex questions where this structure may be appropriate:\n"
    "* 'Explain the project methodology in detail.'\n"
    "* 'What are the key findings and implications of this research?'\n"
    "* 'Compare the different approaches used in this project.'\n"
    "* Questions containing words like: explain, analyze, compare, discuss, elaborate\n\n"
    
    "For visual appeal in complex responses, use:\n"
    "- Emojis for bullet points where appropriate\n"
    "- Bold for important concepts\n"
    "- Proper spacing between sections\n"
    "- Tables for structured data\n"
    "- Code blocks for code examples\n"
    "- Proper translation of sections to the user's language, based on the query. Example: If the user asks in portuguese, you should answer in portuguese, so the sections would be 'Análise mais aprofundada' instead of 'Deeper Dive' and so on. Notice that the translation doesn't need to be literal, you can use the same meaning and intent of the section. This is valid for all languages.\n\n"

    "REMEMBER: Always prioritize giving the most appropriate response type. For simple questions, give simple answers. For complex questions, use structure. When in doubt, prefer simpler formatting.\n"

    r"""If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: The relationship between input variables and the output can often be expressed in a general form, such as ($Y = f(X) + \epsilon$), where ($Y$) is the response variable, ($X$) represents the input variables, ($f$) is an unknown function describing the relationship, and ($\epsilon$) is the error term.. Example: **$X_i$**: The individual data points for the variable $X$. When using block equations $$...$$, when the equation is over, use a new line to start the next text or equation. Example: General Form of the Model: The relationship between the response variable $Y$ and the predictors $X_1$, $X_2$, $\ldots$, $X_p$ can be expressed in a general form:"""
)

# --- Topic Analyzer Agent Prompt ---
TOPIC_ANALYZER_PROMPT = """
You are a specialized topic analyzer. Your ONLY purpose is to identify distinct topics in the user's query and determine which tools should be used for each topic. List the available Tools: {available_tools} and use only the ones that are available. Follow these steps carefully:

1. **Analyze the Query:**
   * Carefully read the user's entire query: {input}
   * Break it down into genuinely distinct, non-overlapping core subjects or topics.
   * **CRITICAL: Group closely related concepts (e.g., 'project objectives', 'expected results', 'project goals') under ONE primary topic if they refer to the same underlying concept.**
   * Identify **Explicit External Information Requests**: Look for phrases like "além disso", "informe mais sobre", "coisas a mais que não aborda", "pesquise", "busque", "baseado na literatura", "quero saber mais".

2. **Tool Assignment (based on the available tools {available_tools}):**
   * For each identified primary topic:
     * Assign the 'retrieve' tool to gather information from documents if 'retrieve' is in {available_tools}.
     * If there's an explicit external information request for this topic AND web search tools are available, also assign the available web search tools ('web', 'academic', 'social') if they are in {available_tools}. If only 'academic' is available, use only 'academic', if 'web' and 'social' are available, use both and so on.
     * IMPORTANT: If {available_tools} only has web search tools, OVERRIDE the first rule and use only web search tools for each topic, regardless if the user explicitly asks for external information of not.
   * Create a concise, keyword-based query (3-5 words max) for each tool-topic pair.

3. **Output Format:**
   * You MUST output a Python list of tuples, where each tuple represents a topic and its associated tool.
   * Each tuple MUST have the following elements:
     * 'query': The concise query for this topic (string)
     * 'tools': Tool name to be used for this topic (string)
   * For example:
     [
        ("critérios rejeição pacientes", "retrieve"),
        ("sintomas osteoarticulares", "retrieve"),
        ("sintomas osteoarticulares", "web"),
        ("sintomas osteoarticulares", "academic")
     ]

Analyze the query and ONLY output the list of topic-tool pairs in the specified format. DO NOT include any explanations or additional text.
"""

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


def create_human_message_with_images(content, image_data_array=None):
    """Creates either a regular HumanMessage or a HumanMessageWithImages based on if image data is provided."""
    if image_data_array and len(image_data_array) > 0:
        # Format the message content with images
        message_content = [
            {
                "type": "text",
                "text": content
            }
        ]
        
        # Add each image to content
        for image_data in image_data_array:
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": image_data
                }
            })
            
        # Return a message with the formatted content
        return HumanMessage(content=message_content)
    else:
        # Return a regular text message
        return HumanMessage(content=content)

# --- Main Chat Function (Updated Tool Handling) ---
def chat(chat_history, vectordb, user_query, use_rag=True, use_web_search=False, search_types=None, model="gpt-4o-mini", image_data=None):
    """
    Main chat function using a two-stage approach for RAG and web search.
    Agent 1: Analyzes the query and identifies topic-tool pairs.
    Function: Executes each tool-topic pair from Agent 1's raw output.
    """
    if not user_query or not user_query.strip():
        if not image_data:  # Only return early if there's no query AND no image
            return "Please provide a query or image.", "", []

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
    tool_name_to_tool = {}  # Map tool names to actual tool functions

    # RAG Tool (Conditional)
    if use_rag and vectordb:
        print("Setting up RAG tool...")
        try:
            @tool(response_format= "content")
            def retrieve(user_query):
                """
                Searches and returns relevant document excerpts and their metadata from the uploaded files.
                """
                retriever = vectordb.as_retriever()
                retrieved_docs = retriever.get_relevant_documents(user_query)
                return retrieved_docs
            
            # Use a consistent name for the RAG tool
            rag_tool_name = "retrieve"
            tools.append(retrieve)
            active_tool_names.add(rag_tool_name)
            tool_name_to_tool[rag_tool_name] = retrieve
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
            s_type = s_type.lower().strip() # Normalize type string
            if s_type in SEARCH_TOOL_MAP:
                tool_instance = SEARCH_TOOL_MAP[s_type]
                tools.append(tool_instance)
                active_tool_names.add(tool_instance.name) # Add the specific tool name
                tool_name_to_tool[tool_instance.name] = tool_instance
                print(f"- Added tool: {tool_instance.name}")
            else:
                print(f"Warning: Unknown search type '{s_type}' requested. Skipping.")
        if not any(tool.name in active_tool_names for tool in SEARCH_TOOL_MAP.values()):
             print("Warning: Web search enabled, but no valid search types resulted in tools being added.")

    # --- Agent/LLM Execution ---
    response_content = ""
    document_metadata = ""
    web_source_info = []

    # Case 1: No Tools (No RAG or Web Search) - Use the selected model directly
    if not tools:
        llm = ChatOpenAI(model=response_model, temperature=0.3, streaming=False)
        print(f"Mode: Standard LLM (No tools available or enabled) using {response_model}")
        
        prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=BASE_SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="chat_history"),
            MessagesPlaceholder(variable_name="user_message")
        ])
        chain = prompt | llm
        
        # Convert single image_data to array if needed
        image_data_array = image_data if isinstance(image_data, list) else ([image_data] if image_data else None)
        user_message = create_human_message_with_images(user_query, image_data_array)
        chat_history.append(user_message)
        
        # Invoke with the user message as a separate variable
        result = chain.invoke({
            "chat_history": chat_history,  # Exclude the message we just added
            "user_message": [user_message]  # Pass as a list for the MessagesPlaceholder
        })
        
        response_content = result.content.strip()
        chat_history.append(AIMessage(content=response_content))

    # Case 2, 3, 4: Use Agent 1 for topic analysis and direct execution for tools
    else:
        # Use gpt-4o-mini for the agent operations
        agent_llm = ChatOpenAI(model=agent_model, temperature=0, streaming=False)
        print(f"Stage 1: Topic analysis using {agent_model}")
        
        try:
            # --- AGENT 1: Topic Analyzer ---
            # Create the topic analyzer prompt
            topic_analyzer_prompt = PromptTemplate.from_template(TOPIC_ANALYZER_PROMPT)
            
            # Create a direct chain without using the agent framework
            topic_analyzer_chain = topic_analyzer_prompt | agent_llm
            
            # Execute the topic analyzer to get topic-tool pairs
            print(f"Available tools: {active_tool_names}")
            topic_analyzer_input = {
                "input": user_query,
                "available_tools": ", ".join(active_tool_names)
            }
            
            topic_analyzer_result = topic_analyzer_chain.invoke(topic_analyzer_input)
            topic_analyzer_output = topic_analyzer_result.content.strip()
            topic_analyzer_output = ast.literal_eval(topic_analyzer_output)
            
            # Print the topic-tool pairs for debugging
            print(f"Topic-Tool Pairs:\n{topic_analyzer_output}")
            
            # --- DIRECT EXECUTION FUNCTION ---
            print(f"Stage 2: Direct tool execution")
            
            # Initialize containers for results
            retrieved_docs_for_display = []
            web_results_for_display = []
            retrieved_context = ""
            web_context = ""
            executed_tools = []       
            
            # Track executed pairs to avoid duplicates
            executed_pairs = set()
            
            # Execute each tool-topic pair
            print("DEBUG - topic_analyzer_output:", topic_analyzer_output)
            print("DEBUG - type:", type(topic_analyzer_output))
            print("DEBUG - contents:", [type(x) for x in topic_analyzer_output])
            for query, tool_name in topic_analyzer_output:
                # Clean up the strings
                query = query.strip()
                tool_name = tool_name.strip()
                
                # Create a unique identifier for this pair
                pair_id = f"{tool_name}:{query}"
                
                # Skip if we've already executed this exact pair
                if pair_id in executed_pairs:
                    print(f"Skipping duplicate tool-topic pair: {pair_id}")
                    continue
                
                # Check if tool exists
                if tool_name not in tool_name_to_tool:
                    print(f"Warning: Tool '{tool_name}' not found, skipping")
                    continue
                
                # Get the tool function
                tool_func = tool_name_to_tool[tool_name]
                
                # Execute the tool
                print(f"Executing tool '{tool_name}' with query: '{query}'")
                try:
                    # Track that we're executing this pair
                    executed_pairs.add(pair_id)
                    executed_tools.append(tool_name)
                    
                    # Call the tool function
                    result = tool_func.invoke({"user_query": query})
                    
                    # Process results based on tool type
                    if use_rag and tool_name == rag_tool_name:
                        # Handle RAG tool results
                        if isinstance(result, list):
                            retrieved_docs_for_display.extend(result)
                            # Extract text content from documents
                            for doc in result:
                                if hasattr(doc, 'page_content'):
                                    retrieved_context += doc.page_content + "\n\n"
                        else:
                            print(f"Warning: RAG tool result was not a list: {type(result)}")
                    
                    elif use_web_search and tool_name in active_tool_names:
                        # Handle web search tool results
                        if isinstance(result, list):
                            web_results_for_display.extend(result)
                            # Extract content from web results
                            for item in result:
                                if isinstance(item, dict) and 'content' in item:
                                    web_context += item['content'] + "\n\n"
                        else:
                            print(f"Warning: Web search tool result was not a list: {type(result)}")
                
                except Exception as e:
                    print(f"Error executing tool '{tool_name}' with query '{query}': {e}")
            
            print(f"Tool execution complete. Executed {len(executed_pairs)} unique tool-topic pairs.")
            
            # Format source information for display
            if use_rag and retrieved_docs_for_display:
                document_metadata = format_document_metadata_for_display(retrieved_docs_for_display)
            if use_web_search and web_results_for_display:
                web_source_info = format_web_results_for_display(web_results_for_display)
            
            # Now use the user's selected model to generate the final response
            response_llm = ChatOpenAI(model=response_model, temperature=0, streaming=False)
            print(f"Stage 3: Generating final response using {response_model}")
            
            # Prepare context from collected information
            final_context = "Information found from documents and web searches:\n\n"
            if retrieved_context:
                final_context += "From documents (RAG):\n" + retrieved_context + "\n\n"
            if web_context:
                final_context += "From web searches:\n" + web_context + "\n\n"
            
            # Use a simpler approach by creating the message directly
            # Customize the prompt based on information sources and restrictions
            strict_instructions = """
            CRITICAL INSTRUCTIONS ON INFORMATION USAGE:

            1. WHEN USING DOCUMENT INFORMATION (RAG):
            - You MUST ONLY respond with information explicitly found in the provided document context.
            - If the documents do not contain information to answer the question, you MUST respond with: "The documents do not provide information about [topic]."
            - DO NOT use your own knowledge to fill gaps in the document information unless explicitly authorized.

            2. WHEN USING WEB SEARCH RESULTS:
            - You may use information from web search results to supplement document information.
            - Clearly indicate which parts of your response come from web searches.
            - If neither documents nor web searches contain the answer, state this clearly.

            3. REGARDING YOUR OWN KNOWLEDGE:
            - You MUST NOT use your built-in knowledge to answer questions when RAG is used.
            - Stick EXCLUSIVELY to information found in the provided context.
            - If RAG was not used, you can use your own knowledge in adition to the context provided to answer the question.
            """
            full_prompt = BASE_SYSTEM_PROMPT + "\n\n" + strict_instructions + "\n\nRespond to the user based on the following context, following the critical instructions above."

            # Create a prompt template with chat history placeholder
            response_prompt = ChatPromptTemplate.from_messages([
                SystemMessage(content=full_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                MessagesPlaceholder(variable_name="user_message")
            ])

            # Create the user message with the context and possible image
            context_text = f"Based on the following information, answer my question: {user_query}\n\nContext from sources:\n{final_context}"
            # Convert single image_data to array if needed
            image_data_array = image_data if isinstance(image_data, list) else ([image_data] if image_data else None)
            user_message = create_human_message_with_images(context_text, image_data_array)

            # Create the chain with the response model
            response_chain = response_prompt | response_llm

            # Invoke with all parameters
            final_response = response_chain.invoke({
                "chat_history": chat_history,
                "user_message": [user_message]  # Pass as a list for the MessagesPlaceholder
            })

            response_content = final_response.content.strip()
            
            # Add to chat history - use the original user query for history
            chat_history.append(create_human_message_with_images(user_query, image_data_array))
            chat_history.append(AIMessage(content=response_content))
            
        except Exception as e:
            print(f"Error during execution: {e}")
            # Log the full traceback for debugging
            import traceback
            traceback.print_exc()
            response_content = f"Sorry, an error occurred while processing your request: {str(e)[:100]}..."
            # Add history for error case
            chat_history.append(create_human_message_with_images(user_query, image_data))
            chat_history.append(AIMessage(content=response_content))

    return response_content, document_metadata, web_source_info