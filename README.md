## Docker Setup
This project uses Docker Compose to run all required services.


### Prerequisites
- Docker and Docker Compose installed
- A `.env` file with your API keys (copy from `.env`)

### Services
The docker-compose.yml includes:

1. MongoDB - Database for product storage (port 27017)
2. Qdrant - Vector database for embeddings (ports 6333, 6334)
3. API - FastAPI server with Inngest functions (port 8000)
4. Inngest - Inngest dev server (port 8288)
5. Streamlit - Web UI (port 8501)

### Usage
1. Copy .env to .env and fill in your credentials:

```bash
cp sample.env .env
```

2. Start all services:
```bash
docker-compose up -d
```

3. View logs:
```bash
docker-compose logs -f
```

4. Stop all services:
```bash
docker-compose down
```
5. Stop and remove volumes(clears data):
```bash
docker-compose down -v
```

### Accessing Services
- Streamlit UI: `http://localhost:8501`
- FastAPI Docs: `http://localhost:8000/docs`
- Inngest Dashboard: `http://localhost:8288`
- Qdrant Dashboard: `http://localhost:6333/dashboard`
- MongoDB: localhost:27017

### Environment Variables
Make sure your `.env` file includes:
- `OPENAI_API_KEY` - For embeddings and LLM
- `THORDATA_USERNAME` - Thordata proxy username
- `THORDATA_PASSWORD` - Thordata proxy password
- `MONGODB_URL` - Override if needed (default: mongodb://mongodb:27017)
- `MONGODB_DATABASE` - Override if needed (default: amazon_price_agent)
- `QDRANT_URL` - Override if needed (default: `http://qdrant:6333`)
- `INNGEST_API_BASE` - Override if needed (default: `http://inngest:8288/v1`)
