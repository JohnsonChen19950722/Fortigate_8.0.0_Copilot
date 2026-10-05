from fastapi import FastAPI

app = FastAPI(debug=False)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}