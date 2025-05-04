from fastapi import FastAPI, HTTPException, Query, Path, Body
import httpx
from typing import List, Optional
import asyncio
from pydantic import BaseModel
from fastapi_mcp import FastApiMCP

app = FastAPI(
    title="Pokemon API",
    description="A fun API for Pokemon enthusiasts",
    version="1.0.0"
)
mcp = FastApiMCP(app)
mcp.mount()

# Base URL for the PokeAPI
POKEAPI_BASE_URL = "https://pokeapi.co/api/v2"

# Famous trainers and their known Pokemon
FAMOUS_TRAINERS = {
    "ash": [
        "pikachu", "charizard", "squirtle", "bulbasaur", "greninja", 
        "infernape", "sceptile", "lycanroc", "dragonite", "gengar"
    ],
    "misty": ["starmie", "staryu", "goldeen", "psyduck", "togepi", "gyarados"],
    "brock": ["onix", "geodude", "vulpix", "crobat", "sudowoodo", "steelix"],
    "gary": ["blastoise", "umbreon", "electivire", "arcanine", "nidoking", "scizor"],
    "lance": ["dragonite", "gyarados", "aerodactyl", "charizard", "tyranitar"],
    "cynthia": ["garchomp", "spiritomb", "milotic", "roserade", "togekiss", "lucario"]
}

# Pokemon regions
POKEMON_REGIONS = {
    "kanto": {"generation": "generation-i", "pokedex": "kanto"},
    "johto": {"generation": "generation-ii", "pokedex": "original-johto"},
    "hoenn": {"generation": "generation-iii", "pokedex": "hoenn"},
    "sinnoh": {"generation": "generation-iv", "pokedex": "original-sinnoh"},
    "unova": {"generation": "generation-v", "pokedex": "original-unova"},
    "kalos": {"generation": "generation-vi", "pokedex": "kalos-central"},
    "alola": {"generation": "generation-vii", "pokedex": "original-alola"},
    "galar": {"generation": "generation-viii", "pokedex": "galar"}
}

# In-memory storage for user's Pokemon team
# Structure: {user_id: [pokemon_details]}
POKEMON_TEAMS = {}

# Models for response
class PokemonBase(BaseModel):
    id: int
    name: str
    types: List[str]
    sprite_url: str

class PokemonDetail(PokemonBase):
    height: int
    weight: int
    abilities: List[str]
    stats: dict
    is_legendary: bool
    is_mythical: bool
    description: Optional[str] = None

class ComparisonResult(BaseModel):
    pokemon: List[PokemonDetail]
    comparison: dict

class TeamResponse(BaseModel):
    user_id: str
    team: List[PokemonDetail]
    team_size: int

class AddPokemonRequest(BaseModel):
    pokemon_name: str

async def fetch_pokemon_data(client, name_or_id):
    """Fetch basic Pokemon data from PokeAPI"""
    try:
        response = await client.get(f"{POKEAPI_BASE_URL}/pokemon/{name_or_id.lower()}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching Pokemon {name_or_id}: {str(e)}")
        return None

async def fetch_pokemon_species(client, name_or_id):
    """Fetch Pokemon species data from PokeAPI"""
    try:
        response = await client.get(f"{POKEAPI_BASE_URL}/pokemon-species/{name_or_id.lower()}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Error fetching Pokemon species {name_or_id}: {str(e)}")
        return None

async def get_pokemon_details(name_or_id):
    """Get detailed Pokemon information combining basic data and species data"""
    async with httpx.AsyncClient() as client:
        pokemon_data = await fetch_pokemon_data(client, name_or_id)
        if not pokemon_data:
            return None
        
        species_data = await fetch_pokemon_species(client, pokemon_data["id"])
        
        # Extract types
        types = [t["type"]["name"] for t in pokemon_data["types"]]
        
        # Extract abilities
        abilities = [a["ability"]["name"].replace("-", " ") for a in pokemon_data["abilities"]]
        
        # Extract stats
        stats = {s["stat"]["name"]: s["base_stat"] for s in pokemon_data["stats"]}
        
        # Get English description if available
        description = None
        if species_data and "flavor_text_entries" in species_data:
            english_entries = [entry for entry in species_data["flavor_text_entries"] 
                              if entry["language"]["name"] == "en"]
            if english_entries:
                description = english_entries[0]["flavor_text"].replace("\n", " ").replace("\f", " ")
        
        return PokemonDetail(
            id=pokemon_data["id"],
            name=pokemon_data["name"],
            types=types,
            sprite_url=pokemon_data["sprites"]["front_default"],
            height=pokemon_data["height"],
            weight=pokemon_data["weight"],
            abilities=abilities,
            stats=stats,
            is_legendary=species_data.get("is_legendary", False) if species_data else False,
            is_mythical=species_data.get("is_mythical", False) if species_data else False,
            description=description
        )

@app.get("/", tags=["General"])
def read_root():
    return {
        "message": "Welcome to the Pokemon API!",
        "endpoints": [
            "/pokemon/{name_or_id}",
            "/pokemon/compare",
            "/pokemon/trainer/{trainer_name}",
            "/pokemon/region/{region_name}",
            "/team/{user_id}",
            "/team/{user_id}/add",
            "/team/{user_id}/remove/{pokemon_name}"
        ]
    }

@app.get("/pokemon/compare", response_model=ComparisonResult, tags=["Pokemon"])
async def compare_pokemon(pokemon_names: List[str] = Query(..., min_length=2, max_length=6)):
    """
    Compare multiple Pokemon (between 2 and 6)
    """
    if len(pokemon_names) < 2:
        raise HTTPException(status_code=400, detail="Please provide at least 2 Pokemon to compare")
    if len(pokemon_names) > 6:
        raise HTTPException(status_code=400, detail="You can compare a maximum of 6 Pokemon")
    
    pokemon_list = []
    async with httpx.AsyncClient() as client:
        tasks = [get_pokemon_details(name) for name in pokemon_names]
        results = await asyncio.gather(*tasks)
        
        for result in results:
            if result:
                pokemon_list.append(result)
    
    if not pokemon_list:
        raise HTTPException(status_code=404, detail="None of the requested Pokemon were found")
    
    # Create comparison data
    comparison = {
        "stats": {},
        "types": {},
        "height": {},
        "weight": {}
    }
    
    # Compare stats
    for stat in ["hp", "attack", "defense", "special-attack", "special-defense", "speed"]:
        comparison["stats"][stat] = {
            "highest": max([(p.name, p.stats.get(stat, 0)) for p in pokemon_list], key=lambda x: x[1]),
            "lowest": min([(p.name, p.stats.get(stat, 0)) for p in pokemon_list], key=lambda x: x[1])
        }
    
    # Compare types
    all_types = set()
    for pokemon in pokemon_list:
        for type_name in pokemon.types:
            all_types.add(type_name)
    
    for type_name in all_types:
        comparison["types"][type_name] = [p.name for p in pokemon_list if type_name in p.types]
    
    # Compare physical attributes
    comparison["height"]["highest"] = max([(p.name, p.height) for p in pokemon_list], key=lambda x: x[1])
    comparison["height"]["lowest"] = min([(p.name, p.height) for p in pokemon_list], key=lambda x: x[1])
    comparison["weight"]["highest"] = max([(p.name, p.weight) for p in pokemon_list], key=lambda x: x[1])
    comparison["weight"]["lowest"] = min([(p.name, p.weight) for p in pokemon_list], key=lambda x: x[1])
    
    return ComparisonResult(pokemon=pokemon_list, comparison=comparison)

@app.get("/pokemon/trainer/{trainer_name}", response_model=List[PokemonDetail], tags=["Pokemon"])
async def get_trainer_pokemon(trainer_name: str):
    """
    Get Pokemon associated with a famous trainer like Ash Ketchum
    """
    trainer_name = trainer_name.lower()
    if trainer_name not in FAMOUS_TRAINERS:
        raise HTTPException(status_code=404, detail=f"Trainer {trainer_name} not found")
    
    pokemon_names = FAMOUS_TRAINERS[trainer_name]
    
    # Get detailed information for each Pokemon
    tasks = [get_pokemon_details(name) for name in pokemon_names]
    results = await asyncio.gather(*tasks)
    
    trainer_pokemon = [result for result in results if result]
    
    return trainer_pokemon

@app.get("/pokemon/region/{region_name}", response_model=List[PokemonDetail], tags=["Pokemon"])
async def get_region_pokemon(region_name: str, limit: int = 20, offset: int = 0):
    """
    Get Pokemon from a specific region (Kanto, Johto, Hoenn, etc.)
    """
    region_name = region_name.lower()
    if region_name not in POKEMON_REGIONS:
        raise HTTPException(status_code=404, detail=f"Region {region_name} not found")
    
    region_info = POKEMON_REGIONS[region_name]
    
    async with httpx.AsyncClient() as client:
        # Get the Pokedex for this region
        response = await client.get(f"{POKEAPI_BASE_URL}/pokedex/{region_info['pokedex']}")
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch region data")
        
        pokedex_data = response.json()
        pokemon_entries = pokedex_data["pokemon_entries"]
        
        # Apply pagination
        paginated_entries = pokemon_entries[offset:offset+limit]
        
        # Get detailed information for each Pokemon
        tasks = [get_pokemon_details(entry["pokemon_species"]["name"]) for entry in paginated_entries]
        results = await asyncio.gather(*tasks)
        
        region_pokemon = [result for result in results if result]
    
    return region_pokemon

# Team management endpoints
@app.get("/team/{user_id}", response_model=TeamResponse, tags=["Team"])
async def get_team(user_id: str = Path(..., description="User ID to get the team for")):
    """
    Get a user's Pokemon team
    """
    if user_id not in POKEMON_TEAMS or not POKEMON_TEAMS[user_id]:
        # Return empty team if user has no team yet
        return TeamResponse(user_id=user_id, team=[], team_size=0)
    
    return TeamResponse(
        user_id=user_id,
        team=POKEMON_TEAMS[user_id],
        team_size=len(POKEMON_TEAMS[user_id])
    )

@app.post("/team/{user_id}/add", response_model=TeamResponse, tags=["Team"])
async def add_to_team(
    user_id: str = Path(..., description="User ID to add Pokemon to"),
    pokemon_request: AddPokemonRequest = Body(..., description="Pokemon to add to the team")
):
    """
    Add a Pokemon to a user's team (maximum 6 Pokemon per team)
    """
    # Initialize team if it doesn't exist
    if user_id not in POKEMON_TEAMS:
        POKEMON_TEAMS[user_id] = []
    
    # Check if team is already full
    if len(POKEMON_TEAMS[user_id]) >= 6:
        raise HTTPException(
            status_code=400, 
            detail="Team is already full (maximum 6 Pokemon). Remove a Pokemon before adding a new one."
        )
    
    # Check if Pokemon already exists in team
    pokemon_names = [p.name for p in POKEMON_TEAMS[user_id]]
    if pokemon_request.pokemon_name.lower() in pokemon_names:
        raise HTTPException(
            status_code=400,
            detail=f"Pokemon {pokemon_request.pokemon_name} is already in your team"
        )
    
    # Get Pokemon details
    pokemon = await get_pokemon_details(pokemon_request.pokemon_name)
    if not pokemon:
        raise HTTPException(
            status_code=404,
            detail=f"Pokemon {pokemon_request.pokemon_name} not found"
        )
    
    # Add to team
    POKEMON_TEAMS[user_id].append(pokemon)
    
    return TeamResponse(
        user_id=user_id,
        team=POKEMON_TEAMS[user_id],
        team_size=len(POKEMON_TEAMS[user_id])
    )

@app.delete("/team/{user_id}/remove/{pokemon_name}", response_model=TeamResponse, tags=["Team"])
async def remove_from_team(
    user_id: str = Path(..., description="User ID to remove Pokemon from"),
    pokemon_name: str = Path(..., description="Name of the Pokemon to remove")
):
    """
    Remove a Pokemon from a user's team
    """
    # Check if user has a team
    if user_id not in POKEMON_TEAMS or not POKEMON_TEAMS[user_id]:
        raise HTTPException(
            status_code=404,
            detail=f"User {user_id} doesn't have a team yet"
        )
    
    # Find Pokemon in team
    pokemon_name = pokemon_name.lower()
    for i, pokemon in enumerate(POKEMON_TEAMS[user_id]):
        if pokemon.name.lower() == pokemon_name:
            # Remove Pokemon
            POKEMON_TEAMS[user_id].pop(i)
            return TeamResponse(
                user_id=user_id,
                team=POKEMON_TEAMS[user_id],
                team_size=len(POKEMON_TEAMS[user_id])
            )
    
    # Pokemon not found in team
    raise HTTPException(
        status_code=404,
        detail=f"Pokemon {pokemon_name} not found in your team"
    )

@app.get("/pokemon/{name_or_id}", response_model=PokemonDetail, tags=["Pokemon"])
async def get_pokemon(name_or_id: str):
    """
    Get detailed information about a specific Pokemon by name or ID
    """
    pokemon = await get_pokemon_details(name_or_id)
    if not pokemon:
        raise HTTPException(status_code=404, detail=f"Pokemon {name_or_id} not found")
    return pokemon

mcp.setup_server()



def main():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
