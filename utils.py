class Utils:
    
    def context_builder(self, user_query):

        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        vector_db = Chroma(
            collection_name="my_collection",
            embedding_function=embedder,
            persist_directory="./chroma_langchain_db"
        )

        results = vector_db.similarity_search_with_relevance_scores(
            query=user_query,
            k=5
        )

        THRESHOLD = 0.90

        context = []

        for i, (doc, score) in enumerate(results, start=1):

            if score >= THRESHOLD:

                context.append({
                    "source_id": i,
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score
                })

        if len(context) == 0:
            return None

        return context   
    
    def load_llm(self):
        from langchain_groq import ChatGroq
        import os 
        from dotenv import load_dotenv

        load_dotenv()

        api_key = os.getenv("GROQ_API_KEY", "").strip()
        llm = None
        tools = None
        startup_error = None

        print("api_key:", repr(api_key))
        print("startup tools:", tools if "tools" in globals() else "not defined")
        if api_key:
            try:
                print("Creating ChatGroq...")
                llm = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    groq_api_key=api_key,
                )
                print("ChatGroq created")
            except Exception as exc:
                startup_error = str(exc)
        else:
            startup_error = (
                "GROQ_API_KEY is not set. Add it to your environment or a .env file "
                "before calling /ask."
            )
    def format_context(self,docs):
        formatted = []
        for d in docs:
            source_id = d.get("source_id", "unknown_id")
            content = d.get("content", "")
            metadata = d.get("metadata", {})
            
            source = metadata.get("source", "unknown_source")
            page = metadata.get("page", "unknown_page")
            
            formatted.append(
                f"[source {source_id} | {source} page {page}]\n{content}\n"
            )
        return "\n".join(formatted)
                
    def generate_answer(self,user_query:str,context:str):
        llm = self.load_llm()

        # Usage
        new_context = self.format_context(context)

        prompt = f"""
        You are a helpful document question-answering assistant.

        Use ONLY the information provided in the context below.

        Rules:
        1. Answer only from the provided context.
        2. Do not use outside knowledge.
        3. If the answer is not present in the context, reply exactly:
        "I couldn't find information related to this question in the uploaded documents."
        4. Cite the source number(s) and page(s) used for each factual statement.
        5. Return the answer in the following structured format:

        user_query: "{user_query}"

        answer1: "<first factual answer>"
        source1: "<source_id | source filename | page>"

        answer2: "<second factual answer>"
        source2: "<source_id | source filename | page>"

        ... continue for all relevant answers ...

        Context:
        {new_context}

        Question:
        {user_query}

        Answer:
        """
        generalized_answer = llm.invoke(prompt)
        return generalized_answer