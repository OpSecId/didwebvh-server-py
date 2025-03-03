from app import create_app
from app.services import AskarStorage, AgentController
import asyncio

app = create_app()

if __name__ == "__main__":
    asyncio.run(AskarStorage().provision(recreate=False))
    asyncio.run(AgentController().provision())
    app.run(host="0.0.0.0", port="5000", debug=True)