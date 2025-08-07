#!/usr/bin/env python3
"""
Character Image Management Script
Helps you add custom images for your AI characters
"""

import json
import os
from pathlib import Path

def load_characters():
    """Load characters from JSON file"""
    with open('characters.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def save_characters(characters):
    """Save characters to JSON file"""
    with open('characters.json', 'w', encoding='utf-8') as f:
        json.dump(characters, f, indent=2, ensure_ascii=False)

def update_character_image(character_id, image_url):
    """Update a character's image URL"""
    characters = load_characters()
    
    for char in characters:
        if char['id'] == character_id:
            char['image_url'] = image_url
            print(f"✅ Updated {char['name']} with image: {image_url}")
            break
    else:
        print(f"❌ Character with ID '{character_id}' not found")
        return False
    
    save_characters(characters)
    return True

def list_characters():
    """List all characters with their current image URLs"""
    characters = load_characters()
    
    print("📋 Current Characters and Images:")
    print("=" * 50)
    
    for char in characters:
        print(f"👤 {char['name']} ({char['age']})")
        print(f"   ID: {char['id']}")
        print(f"   Role: {char['role']}")
        print(f"   Image: {char['image_url']}")
        print(f"   Price: {char['price_stars']} Stars")
        print("-" * 30)

def add_custom_image():
    """Interactive function to add custom images"""
    print("🌟 Add Custom Character Image")
    print("=" * 30)
    
    # List current characters
    characters = load_characters()
    print("\nAvailable characters:")
    for i, char in enumerate(characters, 1):
        print(f"{i}. {char['name']} ({char['role']})")
    
    try:
        choice = int(input("\nSelect character (1-10): ")) - 1
        if 0 <= choice < len(characters):
            char = characters[choice]
            print(f"\nSelected: {char['name']}")
            
            print("\nImage URL options:")
            print("1. Use Picsum Photos (random placeholder)")
            print("2. Use your own image URL")
            print("3. Use local image file")
            
            url_choice = input("\nChoose option (1-3): ")
            
            if url_choice == "1":
                # Use Picsum with specific seed for consistency
                seed = choice + 1
                image_url = f"https://picsum.photos/300/400?random={seed}"
                update_character_image(char['id'], image_url)
                
            elif url_choice == "2":
                image_url = input("Enter image URL: ").strip()
                if image_url:
                    update_character_image(char['id'], image_url)
                else:
                    print("❌ Invalid URL")
                    
            elif url_choice == "3":
                print("\nTo use a local image:")
                print("1. Place your image in the project folder")
                print("2. Enter the filename (e.g., 'priya.jpg')")
                print("3. The image will be served from your server")
                
                filename = input("Enter image filename: ").strip()
                if filename:
                    # Create images directory if it doesn't exist
                    images_dir = Path("images")
                    images_dir.mkdir(exist_ok=True)
                    
                    # Check if file exists
                    image_path = images_dir / filename
                    if image_path.exists():
                        image_url = f"/images/{filename}"
                        update_character_image(char['id'], image_url)
                        print(f"✅ Image set to: {image_url}")
                        print(f"📁 File location: {image_path.absolute()}")
                    else:
                        print(f"❌ File not found: {image_path}")
                        print("Please place the image file in the 'images' folder first")
            else:
                print("❌ Invalid choice")
                
        else:
            print("❌ Invalid character selection")
            
    except ValueError:
        print("❌ Please enter a valid number")
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def main():
    """Main function"""
    print("🎭 Character Image Manager")
    print("=" * 30)
    
    while True:
        print("\nOptions:")
        print("1. List all characters and images")
        print("2. Add custom image")
        print("3. Exit")
        
        choice = input("\nChoose option (1-3): ").strip()
        
        if choice == "1":
            list_characters()
        elif choice == "2":
            add_custom_image()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()
