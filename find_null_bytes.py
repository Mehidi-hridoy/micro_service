# Create a Python script to find files with null bytes
import os
import sys

def check_file_for_null_bytes(filepath):
    """Check if a file contains null bytes."""
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                print(f"NULL bytes found in: {filepath}")
                # Show the line numbers
                lines = content.split(b'\n')
                for i, line in enumerate(lines, 1):
                    if b'\x00' in line:
                        print(f"  Line {i}: {line[:100]}")
                return True
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return False

def check_directory(directory):
    """Check all Python files in a directory for null bytes."""
    null_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                if check_file_for_null_bytes(filepath):
                    null_files.append(filepath)
    return null_files

if __name__ == "__main__":
    directory = '.'  # Current directory
    null_files = check_directory(directory)
    
    if null_files:
        print(f"\nFound {len(null_files)} file(s) with NULL bytes:")
        for file in null_files:
            print(f"  {file}")
        
        print("\nTo fix, you can:")
        print("1. Delete and recreate the affected files")
        print("2. Or run: python -c \"open('filename.py', 'wb').write(open('filename.py', 'rb').read().replace(b'\\\\x00', b''))\"")
    else:
        print("No NULL bytes found in Python files.")
# Run the script
