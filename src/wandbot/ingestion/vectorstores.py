import json
import pathlib

import wandb
from langchain.schema import Document as LcDocument
from llama_index.callbacks import WandbCallbackHandler

from wandbot.ingestion import preprocess_data
from wandbot.ingestion.config import VectorStoreConfig
from wandbot.utils import get_logger, load_index, load_service_context, load_storage_context

logger = get_logger(__name__)


def load(
    project: str,
    entity: str,
    source_artifact_path: str,
    result_artifact_name: str = "wandbot_index",
):
    config = VectorStoreConfig()
    run = wandb.init(project=project, entity=entity, job_type="create_vectorstore")
    artifact = run.use_artifact(source_artifact_path, type="dataset")
    artifact_dir = artifact.download()
    storage_context = load_storage_context(config.embedding_dim, config.persist_dir)
    service_context = load_service_context(
        config.chat_model_name,
        config.temperature,
        config.embeddings_cache,
        config.max_retries,
    )

    document_files = list(pathlib.Path(artifact_dir).rglob("documents.jsonl"))

    transformed_documents = []
    for document_file in document_files:
        documents = []
        with document_file.open() as f:
            for line in f:
                doc_dict = json.loads(line)
                doc = LcDocument(**doc_dict)
                documents.append(doc)
        transformed_documents.extend(preprocess_data.load(documents))

    index = load_index(
        transformed_documents,
        service_context,
        storage_context,
        persist_dir=config.persist_dir,
    )
    wandb_callback = WandbCallbackHandler()

    wandb_callback.persist_index(index, index_name=result_artifact_name)
    wandb_callback.finish()
    run.finish()
    return f"{entity}/{project}/{result_artifact_name}:latest"
