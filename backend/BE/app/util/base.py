from pydantic import BaseModel, ConfigDict


def to_camel(field_name: str) -> str:
    components = field_name.split('_')
    return components[0] + ''.join(x.capitalize() for x in components[1:])

class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel
    )