from pydantic import BaseModel

from ecosim_common.tech.pydantic.alias_generator import to_camel_case


class AppBaseModel(BaseModel):
    model_config = {
        "frozen": True,
        # serialize to camelCase instead snake_case
        "alias_generator": to_camel_case,
        # allow aliases for deserialization (this is needed to be able to deserialize from camelCase)
        "populate_by_name": True,
    }
