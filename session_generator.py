"""
Session String Generator for Pyrogram.
Run this script once to generate your session string.
"""

import asyncio
from pyrogram import Client


async def generate_session():
    """Generate a session string for use with the userbot."""
    
    print("=" * 50)
    print("Pyrogram Session String Generator")
    print("=" * 50)
    print()
    print("You will need:")
    print("1. API_ID and API_HASH from https://my.telegram.org")
    print("2. Your phone number (with country code)")
    print("3. The verification code sent to your Telegram")
    print()
    
    api_id = input("Enter your API_ID: ").strip()
    api_hash = input("Enter your API_HASH: ").strip()
    
    if not api_id or not api_hash:
        print("Error: API_ID and API_HASH are required!")
        return
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("Error: API_ID must be a number!")
        return
    
    print()
    print("Starting authentication...")
    print()
    
    async with Client(
        name="session_generator",
        api_id=api_id,
        api_hash=api_hash,
        in_memory=True
    ) as client:
        # Get the session string
        session_string = await client.export_session_string()
        
        print()
        print("=" * 50)
        print("SUCCESS! Your session string is:")
        print("=" * 50)
        print()
        print(session_string)
        print()
        print("=" * 50)
        print()
        print("IMPORTANT:")
        print("1. Copy the session string above")
        print("2. Add it to your .env file as SESSION_STRING")
        print("3. Keep it SECRET - anyone with this string can access your account!")
        print()


if __name__ == "__main__":
    asyncio.run(generate_session())
