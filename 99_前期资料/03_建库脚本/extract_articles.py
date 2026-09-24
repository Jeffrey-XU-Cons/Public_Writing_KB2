import os
import yaml
from pathlib import Path
import re

# The base directory for the knowledge base
BASE_DIR = Path("d:/projects/Public_Writing_KB")
# The source directory containing the documents to be processed
SOURCE_DIR = BASE_DIR / "00_raw_materials" / "个人历史交付物"
# The output directory for the generated metadata
OUTPUT_DIR = BASE_DIR / "04_corpus"
# The name of the output file
OUTPUT_FILE = OUTPUT_DIR / "个人历史交付物元数据索引.yaml"

def get_word_count(file_path):
    """
    Calculates the word count of a text file.
    
    Args:
        file_path (Path): The path to the file.
        
    Returns:
        int: The number of words in the file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # A simple word count logic based on length, can be refined
            return len(content)
    except Exception as e:
        print(f"  [WARN] Could not read file {file_path}: {e}")
        return 0

def extract_metadata_from_filename(filename):
    """
    Extracts tags and a potential title from the filename.
    
    Args:
        filename (str): The name of the file.
        
    Returns:
        tuple: A tuple containing the extracted title and a list of tags.
    """
    # Remove file extension and clean up the name
    name = Path(filename).stem
    
    # Simple cleanup of common patterns
    name = re.sub(r'[\(（].*?[\)）]', '', name) # Remove anything in parentheses
    name = re.sub(r'v\d+\.\d+', '', name, flags=re.IGNORECASE) # Remove version numbers like v1.0
    name = name.replace('_', ' ').replace('-', ' ').strip()
    
    tags = [tag for tag in name.split() if len(tag) > 1]
    title = name
    
    return title, tags

def process_files():
    """
    Processes all files in the source directory, extracts metadata,
    and saves it to a YAML file.
    """
    all_metadata = []
    
    print(f"Starting metadata extraction from: {SOURCE_DIR}")

    # Ensure the output directory exists
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Walk through all subdirectories and files
    for dirpath, _, filenames in os.walk(SOURCE_DIR):
        dirpath = Path(dirpath)
        category = dirpath.name
        
        # Skip the root directory itself, only process subdirectories
        if dirpath == SOURCE_DIR:
            continue
            
        print(f"\nProcessing category: {category}...")
        
        for filename in filenames:
            if not filename.endswith((".md", ".txt")):
                continue

            file_path = dirpath / filename
            word_count = get_word_count(file_path)
            title, tags = extract_metadata_from_filename(filename)

            entry = {
                'file_path': str(file_path.relative_to(BASE_DIR)).replace('\\', '/'),
                'category': category,
                'title': title,
                'word_count': word_count,
                'source_file_name': filename,
                'tags': tags,
                'quality_score': 0, # Placeholder for manual scoring
            }
            
            all_metadata.append(entry)
            print(f"  - Extracted: {filename}")

    print(f"\nTotal files processed: {len(all_metadata)}")

    # Save the collected metadata to a YAML file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        yaml.dump(all_metadata, f, allow_unicode=True, indent=2, sort_keys=False)

    print(f"\nSuccessfully generated metadata index at: {OUTPUT_FILE}")

def main():
    """
    Main function to run the script.
    """
    process_files()

if __name__ == "__main__":
    main()
