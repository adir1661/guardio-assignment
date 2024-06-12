import re
from typing import Optional

import pydantic

import pokedex_pb2

class PokemonStruct(pydantic.BaseModel):
    number: int
    name: str
    type_one: str
    type_two: Optional[str]
    total: int
    hit_points: int
    attack: int
    defense: int
    special_attack: int
    special_defense: int
    speed: int
    generation: int
    legendary: bool

    @classmethod
    def from_protobuf(
            cls,
            pokemon_proto: pokedex_pb2.Pokemon
    ) -> 'PokemonStruct':
        return cls(
            number=pokemon_proto.number,
            name=pokemon_proto.name,
            type_one=pokemon_proto.type_one,
            type_two=pokemon_proto.type_two if hasattr(pokemon_proto,"type_two") else None,
            total=pokemon_proto.total,
            hit_points=pokemon_proto.hit_points,
            attack=pokemon_proto.attack,
            defense=pokemon_proto.defense,
            special_attack=pokemon_proto.special_attack,
            special_defense=pokemon_proto.special_defense,
            speed=pokemon_proto.speed,
            generation=pokemon_proto.generation,
            legendary=pokemon_proto.legendary,
        )

    def validate_rules(self, rules: list) -> bool:
        for rule in rules:
            if not self.evaluate_rule(rule):
                return False
        return True

    def evaluate_rule(self, rule: str) -> bool:
        # Regex to parse the rule
        match = re.match(r'(\w+)\s*(==|!=|>|<|>=|<=)\s*(\S+)', rule)
        if not match:
            raise ValueError(f"Invalid rule format: {rule}")

        field, operator, value = match.groups()
        actual_value = getattr(self, field)

        # Convert the value to the appropriate type
        if isinstance(actual_value, int):
            value = int(value)
        elif isinstance(actual_value, float):
            value = float(value)
        elif isinstance(actual_value, str):
            value = str(value).strip("'\"")
        elif isinstance(actual_value, bool):
            value = value.lower() in ['true', '1', 'yes']

        return self.compare_values(actual_value, operator, value)

    @staticmethod
    def compare_values(actual, operator, expected):
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == "<":
            return actual < expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<=":
            return actual <= expected
        else:
            raise ValueError(f"Unsupported operator: {operator}")


if __name__ == '__main__':
    # Example binary data from the request
    binary_data = b'\x08\xeb\x01\x12\x08Smeargle\x1a\x06Normal(\xfa\x01078\x14@#H\x14P-XK`\x02'

    # Create a Pokemon instance
    pokemon_proto = pokedex_pb2.Pokemon()

    # Parse the binary data
    pokemon_proto.ParseFromString(binary_data)

    # Convert to Pydantic model
    pokemon_pydantic = PokemonStruct.from_protobuf(pokemon_proto)

    # Define the rules
    rules = [
        "hit_points==20",
        "type_two != 'word'",
        "special_defense > 10",
        "generation < 20"
    ]

    # Validate the rules
    valid = pokemon_pydantic.validate_rules(rules)

    # Print the results
    print("Full parsed message:")
    print(pokemon_pydantic)
    print(f"Validation result: {valid}")
