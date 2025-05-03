# Pokemon API

A fun API for Pokemon enthusiasts built with FastAPI and the [PokeAPI](https://pokeapi.co/).

## Features

This API provides several endpoints to access Pokemon data:

- **Get Pokemon Details**: Get detailed information about a specific Pokemon
- **Compare Pokemon**: Compare stats, types, and attributes of multiple Pokemon
- **Legendary Pokemon**: Get a list of all legendary Pokemon
- **Top Pokemon**: Get the top Pokemon based on base stat total
- **Trainer Pokemon**: Get Pokemon associated with famous trainers like Ash Ketchum
- **Regional Pokemon**: Get Pokemon from specific regions (Kanto, Johto, etc.)
- **Top Regional Pokemon**: Get the top Pokemon from each region

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -e .
   ```

## Usage

Run the server:

```bash
python main.py
```

The API will be available at http://localhost:8000

## API Endpoints

### Get Pokemon Details

```
GET /pokemon/{name_or_id}
```

Example: `GET /pokemon/pikachu` or `GET /pokemon/25`

### Compare Pokemon

```
GET /pokemon/compare?pokemon_names=pikachu&pokemon_names=charizard
```

Compare between 2-6 Pokemon at once.

### Legendary Pokemon

```
GET /pokemon/legendary
```

Optional query parameters:
- `limit`: Number of Pokemon to return (default: 20)
- `offset`: Pagination offset (default: 0)

### Top Pokemon

```
GET /pokemon/top
```

Optional query parameters:
- `limit`: Number of top Pokemon to return (default: 10)

### Trainer Pokemon

```
GET /pokemon/trainer/{trainer_name}
```

Available trainers: ash, misty, brock, gary, lance, cynthia

Example: `GET /pokemon/trainer/ash`

### Regional Pokemon

```
GET /pokemon/region/{region_name}
```

Available regions: kanto, johto, hoenn, sinnoh, unova, kalos, alola, galar

Optional query parameters:
- `limit`: Number of Pokemon to return (default: 20)
- `offset`: Pagination offset (default: 0)

### Top Regional Pokemon

```
GET /pokemon/region/{region_name}/top
```

Optional query parameters:
- `limit`: Number of top Pokemon to return (default: 5)

## Documentation

Interactive API documentation is available at http://localhost:8000/docs when the server is running.