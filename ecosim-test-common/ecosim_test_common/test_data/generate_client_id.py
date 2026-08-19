import random
import uuid

from ecosim_common.config.client_id import ClientID


def generate_random_client_id() -> ClientID:
    return ClientID(
        simulator_name=f"{uuid.uuid4().hex}",
        model_name=f"{random.randint(0, 1000)}",
    )
