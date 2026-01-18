import asyncio
from brightdata import BrightDataClient
import re

restas = [
    ["Matcha Town", "Cupertino Village"],
    ["Hey Tea", "Berkeley"],
    ["85 Bakery", "US"],
]

async def search_restaurants(restas):
    output = []

    async with BrightDataClient(token="a71631ef2aaa7e281e50962740d544a571d94d0acdb80796c98072788f391012") as client:
        for name, location in restas:
            output.append({name: {}})

            results = await client.search.google(
                query=f"{name} {location} coupon OR deal OR promotion"
            )

            if not results.success or not results.data:
                continue

            links = [item.get("url") for item in results.data[:5]]

            insta_pattern = re.compile(r"^https?:\/\/(www\.)?instagram\.com\/")
            social_urls = [u for u in links if insta_pattern.match(u)]

            await scrape_insta(client, social_urls, output[-1][name])

    return output


async def scrape_insta(client, instagram_urls, data):
    for url in instagram_urls:
        results = await client.scrape.instagram.posts(url=url)

        if not results.success or not results.data:
            continue

        post = results.data
        caption = (
            post.get("caption")
            or post.get("description")
            or post.get("edge_media_to_caption", {})
                .get("edges", [{}])[0]
                .get("node", {})
                .get("text")
        )

        if caption:
            data[url] = caption



'''
output = [
    {"Fantasia": {"https://insta...": "captions1", "https://insta2": "captions2}}
    {"Blue Moon": {"https://insta...": "captions3", "https://insta2": "captions4}}
]



'''


'''
async def scrape_facebook(facebook_urls):
    async with BrightDataClient(
        token="a71631ef2aaa7e281e50962740d544a571d94d0acdb80796c98072788f391012"
    ) as client:
        print("Starting Instagram scrape...")

        for url in facebook_urls:
            print(f"\nScraping: {url}")

            results = await client.scrape.facebook.posts(
                url=url
            )

            if not results.success:
                print("Error:", results.error)
                continue

            if not results.data:
                print("No data returned")
                continue

            post = results.data

            # Try common caption fields
            caption = (
                post.get("caption")
                or post.get("description")
                or post.get("edge_media_to_caption", {})
                    .get("edges", [{}])[0]
                    .get("node", {})
                    .get("text")
            )

            if caption:
                print("Caption found:")
                print(caption)
            else:
                print("No caption found")
'''

if __name__ == "__main__":
    result = asyncio.run(search_restaurants(restas))
    print(result)


