import json
import asyncio
from letta_client import AsyncLetta

SYSTEM_PROMPT = """
You are a helpful self-improving agent with file system capabilities.

You will be given an input in the form of a list of dictionaries of dictionaries.

Format:
[
  {
    "Store Name, location": {
        "instagram_link": "caption",
        "instagram_link_2": "caption"
    }
  }
]

Rules:
- Use ONLY the provided input data.
- Do NOT hallucinate deals.
- Prioritize deals specific to the store and its location.
- Each deal entry MUST include:
  - deal_type
  - description
  - price_or_discount
  - availability
  - source_links

For EACH store, you MUST call the generate_deal_entries_json tool exactly once.
Return no text outside of tool calls.
"""


class AsyncLettaReader:
    def __init__(self, LETTA_API_TOKEN: str, AGENT_ID: str):
        self.client = AsyncLetta(
            token=LETTA_API_TOKEN,
            project="default-project",
            timeout=180.0
        )
        self.AGENT_ID = AGENT_ID
        self.agent_state = None

    async def connect_agent(self):
        try:
            self.agent_state = await self.client.agents.retrieve(self.AGENT_ID)
            print("✅ Connected to Letta agent")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to agent: {e}")

    async def read_deals(self, structured_input: list[dict]) -> list[dict]:
        """
        structured_input example:
        [
          {
            "Matcha Town": {
              "https://instagram.com/...": "caption"
            }
          }
        ]
        """

        response = await self.client.agents.messages.create(
            agent_id=self.AGENT_ID,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(structured_input)}
            ]
        )

        results = []

        for message in response.messages:
            if message.message_type == "tool_call_message":
                if message.tool_call.name != "generate_deal_entries_json":
                    continue

                args = json.loads(message.tool_call.arguments)
                results.append(args)

        return results


# ----------------------------
# Example Usage
# ----------------------------

async def get_all_deals(reader: AsyncLettaReader, restaurant_data: list):
    """
    restaurant_data format:
    [
        [store_name, store_dict],
        [store_name2, store_dict2],
        ...
    ]
    """

    data = {}
    for r in restaurant_data:
        store_dict = {r[0]: r[1]}  # wrap dict with store name as key
        deals_info_list = await reader.read_deals([store_dict])
        if deals_info_list:
            # Each store returns exactly one tool call
            deals_info = deals_info_list[0]
            name = deals_info.get('store_name', r[0])
            deals = deals_info.get('deals', [])
            data[name] = deals

    return data


async def main():
    LETTA_API_TOKEN = "sk-let-ZWEzYTQ5MmYtZGJhOS00NmI3LTgzMTUtZjNmODQxYWRkZGYxOjI1MzdhY2FlLTAzYWQtNDM3Yi1iYzQ0LThkMjhmNDNhZDUxZQ=="
    AGENT_ID = "agent-c0d05575-ab51-4d08-9a13-c614e717ef29"

    reader = AsyncLettaReader(LETTA_API_TOKEN, AGENT_ID)
    await reader.connect_agent()

    # Example restaurant input
    restaurant_data = [
        [
            "Matcha Town",
            {
                "https://www.instagram.com/p/DS_lxEQkZgy/":
                "🚨 Grand Opening Jan 16–18 Buy One Get One Free for all drinks, 12% off gelato",
                "https://www.instagram.com/reel/DTQd2_piXtT/":
                "Soft opening until Jan 15, grand opening Jan 16–18 BOGO drinks"
            }
        ]
    ]

    all_deals = await get_all_deals(reader, restaurant_data)
    print(json.dumps(all_deals, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
