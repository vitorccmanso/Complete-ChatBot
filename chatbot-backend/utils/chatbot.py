from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv

def get_llm_chain(with_retriever=True, vectordb=None):
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3, streaming=True)

    if with_retriever and vectordb is not None:
        retriever = vectordb.as_retriever()

        system_prompt = (
            "You are a helpful assistant. You will have to answer to user's queries and ALWAYS give the most complete or longest answer possible to be sure that the user's query was properly answered. "
            "You will give the most complete or longest answer possible unless the user specifies that they want a summary or a short answer. "
            "You will have some context to help with your answers, but it may not always be completely related or helpful. "
            r"""If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: The relationship between input variables and the output can often be expressed in a general form, such as ($Y = f(X) + \epsilon$), where ($Y$) is the response variable, ($X$) represents the input variables, ($f$) is an unknown function describing the relationship, and ($\epsilon$) is the error term.. Example: **$X_i$**: The individual data points for the variable $X$. When using block equations $$...$$, when the equation is over, use a new line to start the next text or equation."""
            "If the user asks for a summary, provide a concise answer. "
            "You can also use your knowledge to assist answering the user's queries."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            ("system", "Here is relevant context to help answer the query: {context}")
        ])

        stuff_chain = create_stuff_documents_chain(llm=llm, prompt=prompt, document_variable_name="context")
        return create_retrieval_chain(retriever, stuff_chain)
    else:
        system_prompt = (
            "You are a helpful assistant. You will answer user's queries as accurately as possible using your own knowledge. "
            "You will have to answer to user's queries and ALWAYS give the most complete or longest answer possible to be sure that the user's query was properly answered. "
            "If the user request equations or math / statistical formulas, format the following mathematical variables and expressions using LaTeX in Markdown so that they are rendered nicely inline with the text. Use single dollar signs $...$ for inline math and double dollar signs $$...$$ for larger centered equations. Make sure all mathematical variables are enclosed in $...$ for inline math formatting. Example: **$X_i$**: The individual data points for the variable $X$. Exmaple: The formula for r is: r = Σ[(Xᵢ - X̅)(Yᵢ - Ȳ)] / √[Σ(Xᵢ - X̅)² * Σ(Yᵢ - Ȳ)²]."
            "If the user asks for a summary, provide a concise answer."
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

        return prompt | llm

def get_response(question, chat_history, vectordb):
    use_retriever = vectordb is not None
    chain = get_llm_chain(with_retriever=use_retriever, vectordb=vectordb)

    inputs = {
        "input": question,
        "chat_history": chat_history,
    }

    if use_retriever:
        response = chain.invoke(inputs)
        return response["answer"], response.get("context", [])
    else:
        response = chain.invoke(inputs)
        if isinstance(response, str):
            return response, []
        return response.content, []

def chat(chat_history, vectordb, user_query):
    # Ensure chat_history is a list of messages
    if user_query is not None and user_query != "":
        chat_history.append(HumanMessage(content=user_query))
        response, context = get_response(user_query, chat_history, vectordb)
        chat_history.append(AIMessage(content=response))

        metadata_dict = defaultdict(list)
        for metadata in [doc.metadata for doc in context]:
            title = metadata.get('title', metadata.get('source', '').split("../docs")[1])
            page_label = metadata.get('page_label', 'Unknown Page')
            metadata_dict[title].append(page_label)

        document_info = "\n".join([f"Document: {title} - Pages: {', '.join(map(str, pages))}" for title, pages in metadata_dict.items()])
        return response, document_info
    return None, None