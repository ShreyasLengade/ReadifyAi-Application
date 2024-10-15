

def insert_newlines(text, max_words=12):
    # Split the input text by existing newlines
    lines = text.split('\n')

    # Process each line
    new_lines = []
    for line in lines:
        words = line.split()

        # If the line has more than max_words, insert newlines
        if len(words) > max_words:
            for i in range(0, len(words), max_words):
                new_lines.append(' '.join(words[i:i+max_words]))
        else:
            new_lines.append(line)

    # Join the processed lines back with newlines
    return '\n'.join(new_lines)


def split_into_pages(text, lines_per_page=30):
    # Split the input text by newlines to work with individual lines
    lines = text.split('\n')

    pages = []  # List to hold all pages
    current_page = []  # List to accumulate lines for the current page

    for line in lines:
        current_page.append(line)
        # Check if the current page has reached the desired number of lines
        if len(current_page) == lines_per_page:
            # Join the lines to form a single string representing the page
            pages.append('\n'.join(current_page))
            current_page = []  # Reset for the next page

    # Don't forget to add the last page if it has less than lines_per_page lines
    if current_page:
        pages.append('\n'.join(current_page))

    return pages


def reformat_text_preserving_newlines(input_file_path, output_file_path, line_length=60):
    """
    Reformat the text in input_file_path so that each line has approximately the
    same number of characters (up to line_length), without splitting words. This
    version preserves original new line characters, treating each original line as
    a separate paragraph. It saves the reformatted text to output_file_path.

    Args:
    input_file_path (str): The path to the input .txt file containing the original text.
    output_file_path (str): The path to the output .txt file to save the reformatted text.
    line_length (int): Desired maximum line length in characters.
    """
    def reformat_paragraph(paragraph, line_length):
        words = paragraph.split()
        current_line = ""
        lines = []

        for word in words:
            if len(current_line) + len(word) + 1 <= line_length:
                current_line += (word + " ")
            else:
                lines.append(current_line.rstrip())  # Remove trailing space
                current_line = word + " "
        lines.append(current_line.rstrip())  # Add last line

        return lines

    with open(input_file_path, 'r', encoding='utf-8') as file:
        paragraphs = file.readlines()

    with open(output_file_path, 'w', encoding='utf-8') as file:
        for paragraph in paragraphs:
            if paragraph.strip():  # Check if the paragraph is not just whitespace
                reformatted_lines = reformat_paragraph(paragraph, line_length)
                for line in reformatted_lines:
                    file.write(line + "\n")
            file.write("\n")  # Preserve paragraph breaks


# # Example usage
# input_file_path = "Tortoise_and_Rabbit/The_Tortoise_and_the_Rabbit.txt"  # Update this path
# output_file_path = "output_file.txt"  # Update this path
# reformat_text_preserving_newlines(
#     input_file_path, output_file_path, line_length=48)
