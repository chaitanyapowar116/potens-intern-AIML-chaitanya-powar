from typing import List, Dict
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader, PyMuPDFLoader
from langchain_community.document_loaders import DirectoryLoader


class Utils:

    def __init__(self):

        load_dotenv()

        print("Initializing Utils...")

        # ---------- Load PDFs ----------
        self.dir_loader = DirectoryLoader(
            "./data",
            glob="**/*.pdf",
            loader_cls=PyMuPDFLoader,
            show_progress=True,
        )

        self.documents = self.dir_loader.load()

        print(f"Loaded {len(self.documents)} documents.")

        # ---------- Split Documents ----------
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        self.split_docs = self.text_splitter.split_documents(self.documents)

        print(
            f"Split {len(self.documents)} documents into {len(self.split_docs)} chunks."
        )

        # ---------- Embedding Model ----------
        self.embedder = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )

        persist_directory = "./chroma_langchain_db"

        # ---------- Load Existing Chroma ----------
        self.vector_db = Chroma(
            collection_name="my_collection",
            embedding_function=self.embedder,
            persist_directory=persist_directory,
        )

        # ---------- Build DB only once ----------
        if self.vector_db._collection.count() == 0:

            print("Creating new Chroma database...")

            self.vector_db.add_documents(self.split_docs)

            print(
                f"Indexed {self.vector_db._collection.count()} document chunks."
            )

        else:

            print(
                f"Loaded existing Chroma database with "
                f"{self.vector_db._collection.count()} chunks."
            )

        # ---------- LLM ----------
        self.llm = self.load_llm()

        print("Utils initialized successfully.\n")

    ###########################################################################

    def load_llm(self):

        api_key = os.getenv("GROQ_API_KEY", "").strip()

        print("GROQ_API_KEY found:", bool(api_key))

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. Please add it to your .env file."
            )

        try:
            print("Creating ChatGroq...")

            llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                groq_api_key=api_key,
            )

            print("ChatGroq created successfully.")

            return llm

        except Exception as exc:
            print("Failed to create ChatGroq:")
            print(exc)
            raise

    ###########################################################################

    def context_builder(self, user_query: str):

        results = self.vector_db.similarity_search_with_score(
        user_query, k=4
        )

        print("\nRetrieved Documents")

        for i, (_, score) in enumerate(results, start=1):
            print(f"Document {i} Score = {score:.4f}")


        context = []

        for i, (doc, score) in enumerate(results, start=1):
            print(f"Loop {i}: score={score}")
            if score > 0.7:
                print(f"Appending document {i}")
                context.append({
                    "source_id": i,
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })

        if not context:
            return None

        return context

    ###########################################################################

    def format_context(self, docs: List[Dict]) -> str:

        formatted = []

        for d in docs:

            source_id = d.get("source_id", "unknown")

            metadata = d.get("metadata", {})

            source = metadata.get("source", "unknown")

            page = metadata.get("page", "unknown")

            content = d.get("content", "")

            formatted.append(
                f"""
[source {source_id}]
File : {source}
Page : {page}

{content}
"""
            )

        return "\n".join(formatted)

    ###########################################################################

    def generate_answer(self, user_query: str, context: List[Dict]):

        if self.llm is None:
            raise RuntimeError("LLM is not initialized.")

        print("\nLLM Object:")
        print(self.llm)
        print(type(self.llm))

        formatted_context = self.format_context(context)
        print(f"\nformatted_context:\n{formatted_context}")

        prompt = f"""
You are a helpful document question-answering assistant.

Your task is to answer the user's question using ONLY the information provided in the Context.

Rules:

1. Use ONLY the provided context. Do NOT use prior knowledge, assumptions, or external information.
2. If the answer cannot be found in the context, reply EXACTLY:
"I couldn't find information related to this question in the uploaded documents."
3. Every answer must be supported by the context.
4. Each answer must be a complete factual statement, not just a word or short phrase.
5. Do NOT repeat the same information. If multiple context chunks contain the same fact, merge them into a single answer and cite the most relevant source.
6. If different sources provide different relevant facts, list each unique fact separately.
7. Do NOT invent, infer, summarize beyond the provided text, or fill in missing information.
8. Preserve the meaning of the original text while writing clear, grammatically correct sentences.
9. Cite the corresponding source number, filename, and page for every answer.
10. Return ONLY as many answer/source pairs as are actually needed. Do NOT generate empty or duplicate answer2, answer3, etc.

Return the answer in exactly the following format:

user_query: "{user_query}"

answer1: "<complete factual answer>"
source1: "<source id | filename | page>"

answer2: "<complete factual answer>"
source2: "<source id | filename | page>"

...

Context:

{formatted_context}

Question:

{user_query}

Answer:
"""

        print("\nSending prompt to Groq...\n")

        try:

            response = self.llm.invoke(prompt)

            print("Groq response received.\n")

            return response

        except Exception as exc:

            print("Error while invoking LLM:")
            print(exc)

            raise

