import logging
from typing import List, Dict, Any

try:
    from langsmith import Client
except ImportError:
    Client = None

from app.core.config import settings
from app.evals.dataset_generator import generate_50_synthetic_cases

logger = logging.getLogger("sync_langsmith")

def sync_dataset_to_langsmith() -> Dict[str, Any]:
    """
    Programmatically creates & updates dataset 'autonomepay-50-eval-benchmark' on LangSmith.
    """
    synthetic_cases = generate_50_synthetic_cases()
    dataset_name = "autonomepay-50-eval-benchmark"

    if not Client or not settings.LANGCHAIN_API_KEY:
        logger.info("LangSmith client or API Key absent. Running in local dataset simulation mode.")
        return {
            "status": "LOCAL_MODE",
            "dataset_name": dataset_name,
            "total_examples": len(synthetic_cases),
            "message": "Local simulation mode active. Synthetic benchmark ready."
        }

    try:
        client = Client(api_key=settings.LANGCHAIN_API_KEY)
        if not client.has_dataset(dataset_name=dataset_name):
            dataset = client.create_dataset(
                dataset_name=dataset_name,
                description="50 synthetic multi-turn revenue recovery evaluation benchmark for AutonomePay"
            )
        else:
            dataset = client.read_dataset(dataset_name=dataset_name)

        for tc in synthetic_cases:
            client.create_example(
                inputs={
                    "scenario_id": tc["scenario_id"],
                    "merchant_id": tc["merchant_id"],
                    "scenario_type": tc["scenario_type"],
                    "simulated_dialogue": tc["dialogue_script"]
                },
                outputs={
                    "expected_action": tc["expected_action"],
                    "expected_amount": tc["expected_amount"]
                },
                dataset_id=dataset.id
            )

        return {
            "status": "SYNCED_TO_LANGSMITH",
            "dataset_id": str(dataset.id),
            "dataset_name": dataset_name,
            "total_examples": len(synthetic_cases)
        }
    except Exception as e:
        logger.warning("LangSmith dataset sync error: %s", str(e))
        return {
            "status": "ERROR_FALLBACK",
            "dataset_name": dataset_name,
            "total_examples": len(synthetic_cases),
            "error": str(e)
        }
