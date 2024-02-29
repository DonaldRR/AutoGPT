from typing import Optional
from pydantic import BaseModel, Field
from autogpt.core.resource.model_providers.schema import ChatMessage

class ChatRequestBody(BaseModel):
    input: str = Field(
        ...,
        min_length=1,
        description="Input prompt"
    )
    additional_input: Optional[dict] = None

class SignInRequestBody(BaseModel):
    user_name: str = Field()
    password: str = Field()

class PetProfileRequestBody(BaseModel):
    
    pet_name: str = Field()
    pet_type: str = Field()
    pet_breed: str = Field()
    desc: str = Field()

class PetProfile(PetProfileRequestBody):

    def fmt_profile(self) -> ChatMessage:
        
        profile = (
            "Pet Profile\n"
            "  Pet Name: {pet_name}\n"
            "  Pet Type: {pet_type}\n"
            "  Pet Breed: {pet_breed}\n"
            "  Pet Description: {desc}"
            ).format(pet_name=self.pet_name,
                     pet_type=self.pet_type,
                     pet_breed=self.pet_breed,
                     desc=self.desc)
        msg = ChatMessage.system(profile)
        
        return msg 