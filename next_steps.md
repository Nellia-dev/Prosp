# Next Steps for Implementing a Fully Operational RAG Pipeline

This document outlines the necessary steps to transition the conceptual Retrieval Augmented Generation (RAG) pipeline (as blueprinted in `prospect/pipeline_orchestrator.py` and `prospect/ai_prospect_intelligence.py`) into a fully functional system.

The current blueprint simulates RAG by:
-   Conceptually chunking text from `enriched_context.md`.
-   Showing where embedding models (`sentence-transformers` example) would generate vector embeddings.
-   Simulating a FAISS vector store for indexing and searching these embeddings.
-   Illustrating how an LLM (`Google Gemini` example) would be called with context retrieved from this store.

To make this operational, the following actions are required:

## 1. Environment Setup & Library Installation

-   **Install Python Libraries**: Ensure all necessary libraries are installed in your Python environment.
    ```bash
    pip install sentence-transformers faiss-cpu numpy google-generativeai loguru
    # Or faiss-gpu if you have a compatible GPU and CUDA setup
    # Add any other utility libraries you might need (e.g., for advanced text splitting)
    ```
-   **API Keys & Credentials**:
    -   **Google Gemini**: Obtain an API key from Google AI Studio (or your Google Cloud project). Set this key as an environment variable (e.g., `GEMINI_API_KEY`). The code currently uses `os.getenv("GEMINI_API_KEY")`.
-   **Model Downloads**:
    -   The chosen embedding model (e.g., `'all-MiniLM-L6-v2'` for `sentence-transformers`) will be downloaded automatically by the library on first use if not already cached locally. Ensure network access for this.

## 2. Implement Real Embedding Generation

-   **In `prospect/pipeline_orchestrator.py` (`PipelineOrchestrator` class):**
    -   **`__init__`**: Uncomment and activate the `SentenceTransformer` initialization:
        ```python
        # self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        # logger.info("SentenceTransformer model loaded.")
        ```
        to
        ```python
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("SentenceTransformer model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}. Embeddings will not be real.")
            self.embedding_model = None
        ```
    -   **`_generate_embeddings`**: Uncomment the actual embedding generation line:
        ```python
        # actual_embeddings_np = self.embedding_model.encode(text_chunks, convert_to_tensor=False, show_progress_bar=True)
        # return actual_embeddings_np.astype('float32')
        ```
        to
        ```python
        actual_embeddings_np = self.embedding_model.encode(text_chunks, show_progress_bar=False) # show_progress_bar can be True for debugging
        return actual_embeddings_np.astype(np.float32)
        ```
        Ensure `numpy` (`np`) is correctly imported and used.

## 3. Implement Real Vector Store Operations (FAISS)

-   **In `prospect/pipeline_orchestrator.py` (`_setup_rag_for_job` method):**
    -   Uncomment and activate the FAISS index creation and population logic:
        ```python
        # logger.info(f"[{job_id}] Initializing FAISS Index (IndexFlatL2) with dimension {embedding_dim}.")
        # index = faiss.IndexFlatL2(embedding_dim)
        # logger.info(f"[{job_id}] Adding {chunk_embeddings_np.shape[0]} embeddings to FAISS index.")
        # index.add(chunk_embeddings_np)
        # self.job_vector_stores[job_id] = {
        #     "index": index,
        #     "chunks": text_chunks,
        #     "embedding_dim": embedding_dim
        # }
        # logger.info(f"[{job_id}] RAG setup complete. FAISS index populated for job.")
        ```
        to (ensure `np` and `faiss` are imported):
        ```python
        logger.info(f"[{job_id}] Initializing FAISS Index (IndexFlatL2) with dimension {embedding_dim}.")
        index = faiss.IndexFlatL2(embedding_dim)
        logger.info(f"[{job_id}] Adding {chunk_embeddings_np.shape[0]} embeddings to FAISS index.")
        index.add(chunk_embeddings_np) # chunk_embeddings_np should already be float32
        self.job_vector_stores[job_id] = {
            "index": index,
            "chunks": text_chunks,
            "embedding_dim": embedding_dim
        }
        logger.info(f"[{job_id}] RAG setup complete. FAISS index populated for job.")
        ```

## 4. Implement Real Query Embedding and Vector Search

-   **In `prospect/ai_prospect_intelligence.py` (`AdvancedProspectProfiler._generate_predictive_insights` method):**
    -   **`__init__`**: Uncomment and activate `SentenceTransformer` initialization (similar to Orchestrator, or consider passing the model instance from Orchestrator if appropriate for your design).
    -   **Query Embedding**: Uncomment the actual query embedding line:
        ```python
        # query_embedding_np = self.embedding_model.encode([query])[0].astype(np.float32)
        ```
        to
        ```python
        query_embedding_np = self.embedding_model.encode([query])[0].astype(np.float32)
        ```
    -   **Vector Store Search**: Uncomment and activate the FAISS search logic:
        ```python
        # D, I = faiss_index.search(np.expand_dims(query_embedding_np, axis=0), k=min(3, len(stored_chunks)))
        # retrieved_chunks_texts = [stored_chunks[i] for i in I[0] if i < len(stored_chunks)]
        ```
        to
        ```python
        D, I = faiss_index.search(np.expand_dims(query_embedding_np, axis=0), k=min(3, len(stored_chunks)))
        retrieved_chunks_texts = [stored_chunks[i] for i in I[0] if i < len(stored_chunks)]
        ```

## 5. Implement Real LLM Calls (Google Gemini)

-   **In `prospect/ai_prospect_intelligence.py` (`AdvancedProspectProfiler._generate_predictive_insights` method):**
    -   **`__init__`**: Uncomment and activate the Google Gemini client initialization (`genai.GenerativeModel`), ensuring `GEMINI_API_KEY` is correctly set in the environment.
        ```python
        # try:
        #     gemini_api_key = os.getenv("GEMINI_API_KEY")
        #     # ... (rest of the initialization) ...
        # except Exception as e:
        #     # ...
        ```
        to actual execution code.
    -   **LLM Call**: Uncomment and activate the Gemini LLM call:
        ```python
        # response = self.llm_client.generate_content(llm_prompt)
        # llm_output = response.text
        # ... (parsing logic) ...
        ```
        to actual execution code. Ensure the `llm_prompt` is well-structured for Gemini.

## 6. Robustness and Error Handling

-   Review all new code involving external calls (model loading, API calls, file I/O) and add comprehensive error handling (try-except blocks, retries if appropriate, status checks).
-   Consider edge cases: empty context files, very short lead descriptions, API rate limits, network issues.

## 7. Text Chunking Strategy

-   The current `_chunk_text` in `PipelineOrchestrator` is very basic. Evaluate and implement a more sophisticated text chunking strategy. Libraries like `LangChain` offer various splitters (`RecursiveCharacterTextSplitter`, `MarkdownHeaderTextSplitter`) that can respect document structure or semantic boundaries.

## 8. Asynchronous Operations

-   For production, especially if dealing with many leads or large context files, consider making I/O-bound and CPU-bound operations (like API calls, file operations, embedding generation for large texts) truly asynchronous using `asyncio` and `aiohttp` (for LLM calls if client library supports it) or running CPU-bound tasks in thread pools (`asyncio.to_thread`). The `encode` method of `sentence-transformers` is CPU-bound.

## 9. Testing

-   **Unit Tests**: Write unit tests for individual components (chunking, embedding function, RAG prompt formulation).
-   **Integration Tests**: Test the flow of context from file to vector store to LLM prompt.
-   **End-to-End Tests**: Test the entire pipeline with sample `job_id`s and `lead_data` to ensure the generated insights are relevant and contextually informed.
-   **Quality Evaluation**: Assess the quality of the retrieved context and the final LLM-generated insights. This is often an iterative process involving prompt engineering and tuning of the retrieval mechanism.

## 10. Production Considerations

-   **Persistent Vector Store**: For production, an in-memory FAISS index per job might be insufficient if jobs are long-lived or context is very large. Consider a persistent vector database solution (e.g., ChromaDB on disk, a managed cloud service like Pinecone, Weaviate, etc.) if scalability and persistence are required beyond single job runs.
-   **Scalability**: Ensure the pipeline can handle the expected load of leads and context processing.
-   **Monitoring & Logging**: Expand logging to monitor the performance and health of the RAG pipeline components.
-   **Cost Management**: Be mindful of API costs for embedding generation (if using API-based models) and LLM calls.

By following these steps, the conceptual RAG blueprint can be transformed into a powerful, production-ready system.
