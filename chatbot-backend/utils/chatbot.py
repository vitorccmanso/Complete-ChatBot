from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv

BASE_SYSTEM_PROMPT = (
    "You are a helpful assistant. You will have to answer to user's queries and ALWAYS give the most complete or longest answer possible to be sure that the user's query was properly answered. "
    "You will give the most complete or longest answer possible unless the user specifies that they want a summary or a short answer. "
    r"""If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: The relationship between input variables and the output can often be expressed in a general form, such as ($Y = f(X) + \epsilon$), where ($Y$) is the response variable, ($X$) represents the input variables, ($f$) is an unknown function describing the relationship, and ($\epsilon$) is the error term.. Example: **$X_i$**: The individual data points for the variable $X$. When using block equations $$...$$, when the equation is over, use a new line to start the next text or equation. Example: General Form of the Model: The relationship between the response variable $Y$ and the predictors $X_1$, $X_2$, $\ldots$, $X_p$ can be expressed in a general form:"""
    "If the user asks for a summary, provide a concise answer. "
)


def get_llm_chain(with_retriever=True, vectordb=None, with_web_search=False):
    """
    Create an LLM chain with the appropriate components based on the scenario.
    
    This function handles 4 cases:
    1. with_retriever=True, with_web_search=True - Use both document retrieval and web search
    2. with_retriever=True, with_web_search=False - Use only document retrieval (RAG)
    3. with_retriever=False, with_web_search=True - Use only web search
    4. with_retriever=False, with_web_search=False - Use only the LLM's knowledge
    
    Args:
        with_retriever (bool): Whether to use document retrieval
        vectordb (VectorStore): The vector database for document retrieval
        with_web_search (bool): Whether to use web search
        
    Returns:
        Chain: The appropriate LangChain chain for the scenario
    """
    load_dotenv()

    # Case 1 & 2: Using retriever (RAG) with or without web search
    if with_retriever and vectordb is not None:
        llm_rag = ChatOpenAI(model="gpt-4o-mini", temperature=0, streaming=True)
        retriever = vectordb.as_retriever()

        # System prompt for RAG scenarios
        system_prompt = BASE_SYSTEM_PROMPT + (
            "CRITICAL INSTRUCTIONS: You are an AI assistant that EXCLUSIVELY uses information from the provided document context to answer questions. "
            "1. You MUST ONLY use the exact information found in the document context provided below. "
            "2. If the document context does not contain the answer, you MUST reply: 'The documents do not contain information about [topic].' "
            "3. DO NOT use any prior knowledge that is not in the document context. "
            "4. DO NOT generate explanations beyond what is directly stated in the documents. "
            "5. DO NOT attempt to be helpful by supplementing with your own knowledge. "
            "6. Include specific citations from the document when answering. "
        
            "If web search results are provided: "
            "- You may use these as a secondary source if the document context is insufficient "
            "- Clearly indicate when information comes from web search rather than document context "

            "Remember: ANY information not found in the provided documents or web search results MUST NOT be included in your response. "

            "When answering, clearly distinguish between information from documents, web search results."
            "Always cite your sources accurately and clearly."
        )
        

        # Build the prompt based on whether web search is enabled
        messages = [
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("system", "Here is relevant context from documents: {context}")
        ]
        
        # Add web context message if web search is enabled
        if with_web_search:
            messages.append(("system", "Here is relevant information from web search: {web_context}"))

        prompt = ChatPromptTemplate.from_messages(messages)
        stuff_chain = create_stuff_documents_chain(llm=llm_rag, prompt=prompt, document_variable_name="context")
        return create_retrieval_chain(retriever, stuff_chain)
    
    # Case 3 & 4: No retriever (no RAG) - just LLM with or without web search
    else:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, streaming=True)
        # Base system prompt for all scenarios
        system_prompt = BASE_SYSTEM_PROMPT
        
        # Add web search specific instructions if enabled
        if with_web_search:
            system_prompt += """
            You will also have access to web search results that provide recent information from the internet.
            When answering, clearly distinguish between web search results and your own knowledge.
            Always cite your sources accurately and clearly.
            """
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                ("system", "Here is relevant information from web search: {web_context}")
            ])
        else:
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}")
            ])

        return prompt | llm

def format_web_results(web_results, max_content_chars=1000):
    """
    Format web search results for LLM consumption.
    
    Args:
        web_results (list): List of dictionaries with web search results
        max_content_chars (int): Maximum characters to include for each result's content
        
    Returns:
        tuple: (web_context, web_results) - formatted context and results
    """
    if not web_results:
        return "", []
    
    # Limit context to 5 results for the LLM (to avoid token limit issues)
    context_results = web_results[:5]
    web_context = "Web search results:\n\n"
    
    for i, result in enumerate(context_results):
        web_context += f"{i+1}. Title: {result['title']}\n"
        web_context += f"   URL: {result['url']}\n"
        content = result['content']
        # Truncate content if needed
        if len(content) > max_content_chars:
            content = content[:max_content_chars] + "..."
        web_context += f"   Content: {content}\n\n"
    
    return web_context, web_results

def get_response(question, chat_history, vectordb, web_results=None):
    """
    Generate a response based on the query, chat history, and available data sources.
    
    Args:
        question (str): The user's query
        chat_history (list): List of previous messages
        vectordb (VectorStore): The vector database for document retrieval
        web_results (list, optional): Results from web search
        
    Returns:
        tuple: (response, context, web_sources) - The AI response, document context, and web sources
    """
    use_retriever = vectordb is not None
    use_web_search = web_results and len(web_results) > 0
    
    # Get the appropriate chain based on available data sources
    chain = get_llm_chain(
        with_retriever=use_retriever, 
        vectordb=vectordb,
        with_web_search=use_web_search
    )

    # Prepare inputs for the chain
    inputs = {
        "input": question,
        "chat_history": chat_history,
    }
    
    # Add web context if available
    if use_web_search:
        web_context, web_sources = format_web_results(web_results)
        inputs["web_context"] = web_context
    else:
        web_sources = []

    # Get response from the chain
    if use_retriever:
        response = chain.invoke(inputs)
        return response["answer"], response.get("context", []), web_sources
    else:
        response = chain.invoke(inputs)
        if isinstance(response, str):
            return response, [], web_sources
        return response.content, [], web_sources

def combine_search_results(results_by_type, max_results=10):
    """
    Combine search results from different types (web, academic, social) in a round-robin fashion
    to ensure diversity of results.
    
    Args:
        results_by_type (dict): Dictionary mapping search types to their respective results
        max_results (int): Maximum number of results to return
        
    Returns:
        list: Combined search results with diversity across types
    """
    combined_results = []
    
    # Add the top results from each search type in a round-robin fashion
    remaining_types = list(results_by_type.keys())
    while remaining_types and len(combined_results) < max_results:
        for search_type in list(remaining_types):  # Use a copy for iteration
            if results_by_type[search_type]:
                # Take the first/best result from this type
                combined_results.append(results_by_type[search_type].pop(0))
                
                # If we've used all results from this type, remove it from rotation
                if not results_by_type[search_type]:
                    remaining_types.remove(search_type)
                    
            # Check if we've reached our limit
            if len(combined_results) >= max_results:
                break
    
    return combined_results

def perform_search_by_types(query, search_types, max_results_per_type=10):
    """
    Perform web searches for each enabled search type and store results by type.
    
    Args:
        query (str): Search query to use
        search_types (list): List of search types to use (web, academic, social)
        max_results_per_type (int): Maximum results to fetch per search type
        
    Returns:
        dict: Dictionary mapping search types to their results
    """
    from utils.web_search import perform_tavily_search
    
    results_by_type = {}
    
    # Perform search for each enabled search type
    for search_type in search_types:
        print(f"Performing {search_type} search with query: {query}")
        results = perform_tavily_search(query, search_type=search_type, max_results=max_results_per_type)
        if results:
            results_by_type[search_type] = results
    
    return results_by_type

def optimize_web_search_query(user_query, doc_context, max_length=200):
    """
    Create an optimized web search query based on the user's question and document context.
    
    This function intelligently decides whether to use the original user query
    or create an enhanced query by extracting key information from document context.
    
    Args:
        user_query (str): The user's original question
        doc_context (str): The full document context text
        max_length (int): Maximum character length for the query
        
    Returns:
        str: An optimized web search query
    """
    try:
        # Truncate doc_context if it's very large to prevent token limits
        truncated_doc = doc_context[:200000] if len(doc_context) > 200000 else doc_context
        
        # Initialize a model for query optimization
        optimizer = ChatOpenAI(temperature=0, model="gpt-3.5-turbo")
        
        # Create a prompt that handles both tasks: analyzing the query and transforming if needed
        system_prompt = """
        Your task is to create the optimal web search query based on the user's question and document context.
        
        Follow these steps:
        
        1. FIRST: Evaluate if the user's original question is already a good web search query:
           - Is it clear, specific, and focused?
           - Does it contain proper search terms?
           - Is it already well-optimized for search engines?
           - Does it NOT directly reference "the document" or "the paper"?
        
        2. If the original question is already a good web search query, return EXACTLY the user's question with no changes.
        
        3. If the original question needs enhancement (it's vague, references the document directly, or lacks specificity), 
           create an optimized search query by:
           - Extracting the key factual information from the document context relevant to the user's question
           - Including important technical terms and concepts from the document
           - Formatting as a concise search query with exact phrases in quotation marks
           - Focusing on objective, searchable information
        
        4. Return ONLY the search query with no explanations or additional text.
        
        Examples:
        
        Example 1 - Good original query:
        User question: "What is statistical learning?"
        Document context: "Statistical learning theory was developed by Vladimir Vapnik..."
        Output: What is statistical learning?
        
        Example 2 - Query needs enhancement:
        User question: "Tell me more about the methods mentioned in the document"
        Document context: "The paper employs gradient boosting decision trees and random forests for anomaly detection..."
        Output: "gradient boosting decision trees" "random forests" "anomaly detection" methods
        """
        
        # Use the optimizer to generate the query
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User question: {user_query}\nDocument context: {truncated_doc}"}
        ]
        
        optimized_query = optimizer.invoke(messages).content
        
        # Ensure length constraints
        if len(optimized_query) > max_length:
            # If too long, truncate at a sentence boundary
            truncated_query = optimized_query[:max_length]
            last_period = truncated_query.rfind('.')
            if last_period > max_length // 2:  # Ensure we don't cut too short
                truncated_query = truncated_query[:last_period + 1]
            optimized_query = truncated_query
        
        print(f"Generated optimized query: {optimized_query}")
        return optimized_query
    
    except Exception as e:
        print(f"Error during query optimization: {str(e)}")
        # Fall back to using the original user query if optimization fails
        print(f"Using original query as fallback: {user_query}")
        return user_query

def chat(chat_history, vectordb, user_query, web_results=None, use_rag=True, use_web_search=False, search_types=None):
    """
    Main chat function that handles both document retrieval and web search.
    
    This function supports 4 scenarios based on RAG and web search toggles:
    1. Both RAG and web search enabled - Cross-reference documents with web search
    2. Only RAG enabled - Use only document context
    3. Only web search enabled - Use only web search results 
    4. Neither enabled - Use only the LLM's knowledge
    
    Args:
        chat_history (list): List of previous messages
        vectordb (VectorStore): The vector database for document retrieval
        user_query (str): The user's query
        web_results (list, optional): Pre-fetched web results (if any)
        use_rag (bool): Whether to use document retrieval (RAG)
        use_web_search (bool): Whether to use web search
        search_types (list): List of search types to use (web, academic, social)
        
    Returns:
        tuple: (response, document_info, web_sources) - The AI response, document info, and web sources
    """
    # Set default search types if none provided
    if search_types is None or not search_types:
        search_types = ["web"]
        
    print(f"Using search types: {search_types}")
    
    # Process query only if one is provided
    if not user_query or user_query.strip() == "":
        return None, None, []
        
    # Add user message to history
    chat_history.append(HumanMessage(content=user_query))
    
    # Determine which retrieval methods to use
    has_vectordb = vectordb is not None
    should_use_rag = has_vectordb and use_rag
    
    # STEP 1: First retrieve document context if RAG is enabled
    doc_context = ""
    if should_use_rag:
        # Get document context first for potential web search enhancement
        retriever = vectordb.as_retriever()
        retrieved_docs = retriever.get_relevant_documents(user_query)
        
        # Extract and combine relevant information from documents
        # Limited to 3 documents to maintain focus and avoid token limits
        if retrieved_docs:
            doc_context = "\n".join([doc.page_content for doc in retrieved_docs])
            
    # STEP 2: Perform web search if enabled
    if use_web_search and web_results is None:
        # Cross-reference with document context if both RAG and web search are enabled
        if should_use_rag and doc_context:
            # Create an optimized search query in one step
            enhanced_query = optimize_web_search_query(user_query, doc_context)
            
            print(f"Enhanced query length: {len(enhanced_query)} characters")
            print(f"Enhanced query: {enhanced_query}")
            
            # Perform searches for each type and combine results
            results_by_type = perform_search_by_types(enhanced_query, search_types, max_results_per_type=10)
            web_results = combine_search_results(results_by_type, max_results=10)
        else:
            # Regular web search without document context - use original query
            results_by_type = perform_search_by_types(user_query, search_types, max_results_per_type=10)
            web_results = combine_search_results(results_by_type, max_results=10)
    
    # STEP 3: Get the final response using the appropriate contexts
    # If RAG is disabled, pass None instead of vectordb
    actual_vectordb = vectordb if should_use_rag else None
    response, context, web_sources = get_response(user_query, chat_history, actual_vectordb, web_results)
    chat_history.append(AIMessage(content=response))

    # Format document metadata (only when RAG is used and context is returned)
    document_info = ""
    if should_use_rag and context:
        metadata_dict = defaultdict(set)
        for metadata in [doc.metadata for doc in context]:
            title = metadata.get('title', metadata.get('source', '').split("../docs")[1])
            page_label = metadata.get('page_label', 'Unknown Page')
            metadata_dict[title].add(int(page_label))

        # Sort the pages for each document for consistent display
        document_info = "\n".join([f"Document: {title} - Pages: {', '.join(str(p) for p in sorted(pages))}" for title, pages in metadata_dict.items()])
    
    return response, document_info, web_sources