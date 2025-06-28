  # Python File Organizer
#### Video Demo:  <URL HERE>

### Features

- Automatically scans and organizes files in a specified directory
- Groups files by type: documents, videos, word files, excel files, etc.
- Creates a “Documents” folder with categorized subfolders
- Customizable file types and folder structure via "data_dict.py"
- Supports command-line and interactive (prompt-based) modes
- Can save a default path for future runs

    #### Description: File Organizer is a simple tool built to help automate the tedious task of organizing files on your computer into categorized folders, based on file type.

    This project was created with the intention of solving a problem I’ve had for a long time: organizing the files on my computer. The basic functionality of my program is to detect files in a specified directory and organize them inside a “Documents” folder, within which are specific subfolders for each type of file, such as:
• pdf
• docx, doc (Word files)
• pptx, ppt (PowerPoint files)
• csv (Excel files)
• png, jpeg, jpg, gif (Image files)
• mp4 (Video files)
• mp3 (Audio files)
The files to be organized can be customized by editing the file named “data_dict.py”, which contains a list of dictionaries. Each dictionary has a key called “Folder”, which represents the name of the folder where files of that type will be stored. For example, the first dictionary may have the folder name “PDF”, which corresponds to a second key called “Suffixes”. This second key holds the list of file extensions that should be placed in that folder.
Regarding the “project.py” file, it works by obtaining a path from the user, either through user input (prompt) or through command-line arguments, depending on user preference. If the user simply runs the program, it will prompt them to enter a path to organize. If no input is given, it will use the default path, which by default is the Desktop (if it's the first time running the program). If the user provides a path, the program checks whether it exists. If it does, the user is asked whether that path should be set as the new default. If they agree, the new path is stored in an external text file, overwriting any previous value stored there.
If the user chooses to run the program via command line using arguments, they must provide the desired path (in quotes, e.g., “D:\test”), and optionally, the flag --set-default ,or -sd for short, to set that path as the new default this works the same as answering “yes” (or “y”)  to the prompt previously mentioned.
After obtaining a valid path, the program scans the specified directory for files, using regular expressions in order to get only the name of the file and it’s extension, and stores it in a list. This list is then passed to another function, which creates (if necessary) a “Documents” folder and, within it, individual folders for each file type found in the list. Finally, the program organizes the files by moving each one into its appropriate folder, matching file extensions to the “Suffixes” values in data_dict.py and placing them in their corresponding “Folder”.

