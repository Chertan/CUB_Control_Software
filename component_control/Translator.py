from CUBExceptions import *
import louis

# Converts from Unified English Braille to the CUB Braille Cell Format
ueb_to_br = {
    'a': "100000", 'b': "110000", 'c': "100100", 'd': "100110",  'e': "100010", 'f': "110100", 'g': "111100",
    'h': "110010", 'i': "010100", 'j': "010110", 'k': "101000",  'l': "111000", 'm': "101100", 'n': "101110",
    'o': "101010", 'p': "111100", 'q': "111110", 'r': "111010",  's': "011100", 't': "011110", 'u': "101001",
    'v': "111001", 'w': "010111", 'x': "101101", 'y': "101111",  'z': "101011", ',': "000001", '#': "001111",
    '0': "001011", '1': "010000", '2': "011000", '3': "010010",  '4': "010011", '5': "110001", '6': "011010",
    '7': "011011", '8': "011001", '9': "001010", '\"': "000010", '<': "110001", '>': "001110", '\'': "001000",
    '.': "000101", "-": "001001", "_": "000111", "?": "100111",  "`": "000100", "&": "111101", "/": "001100",
    "+": "001101", "=": "111111", "!": "011101", "}": "110111",  "|": "110011", "*": "100001", ';': "000011",
    ':': "100011", '(': "111011", ")": "011111", '~': "000110",  '%': "100101", '{': "010101", '\\': "BACKSPACE",
    '\\t': "TAB", " ": "000000"
}

# Converts from Braille Keyboard Code to the CUB Braille Cell Format
b_keyboard_to_br = {
    'the': "011101", '<contract1>': "000010", "<number>": "001111", "ed": "110101", "sh": "100101", "and": "111101",
    '\'': "001000", 'of': "111011", 'with': "011111", 'ch': "100001", 'ing': "001101", '<uppercase>': "000001",
    '-': "001001", '<italic>': "000101", 'st': "001100", '\"': "001011", ',': "010000", ';': "011000", ':': "010010",
    '.': "010011", 'en': "010001", '!': "011010", '(': "011011", ')': "011011", '?': "011001", 'in': "001010",
    'wh': "100011", '<letter>': "000011", 'gh': "110001", 'for': "111111", 'ar': "001110", 'th': "100111",
    '<accent>': "000100", " ": "000000",
    'a': "100000", 'b': "110000", 'c': "100100",   'd': "100110", 'e': "100010", 'f': "110100",  'g': "111100",
    'h': "110010", 'i': "010100", 'j': "010110",   'k': "101000", 'l': "111000", 'm': "101100",  'n': "101110",
    'p': "111100", 'q': "111110", 'r': "111010",   's': "011100", 't': "011110", 'u': "101001",  'v': "111001",
    'w': "010111", 'x': "101101", 'y': "101111",   'z': "101011", 'ow': "010101", 'ou': "110011", 'er': "110111",
    '$': "000110", '<contract2>': "000111"
}


def translate(in_string, in_lang, grade=1):
    """Translates the input word in english into a string where each character represents a Braille Cell

    :param in_string: The string or character to be translated
    :param in_lang: Language/Format of the input string
    :param grade: Grade of Unified English Braille to use for the translation (higher grade has more contractions)
    :return: A list of the translated characters
    """
    # Translate english strings into braille
    if in_lang == "ENG":
        # Convert as per the input grade (default of 1)
        if grade == 1:
            braille = louis.translateString(['en-ueb-g1.ctb'], in_string)
        elif grade == 2:
            braille = louis.translateString(['en-ueb-g2.ctb'], in_string)
        else:
            # Ensures grade is valid
            raise OperationError("Input Conversation", "Translation", "Invalid Grade of Unified English Braille")
    else:
        braille = in_string

    output = []

    # Iterate through the string and convert each symbol to its cell description equivalent
    if in_lang == "BKB":
        # Convert as per Braille Keyboard Specification
        output.append(b_keyboard_to_br[braille])
    else:
        for char in braille:
            if in_lang == "ENG" or in_lang == "UEB":
                # Converted character as per UEB Specification
                output.append(ueb_to_br[char])
            else:
                # Invalid language set - Should never reach in operation as argument parser should prevent
                # Left here in case of abnormal circumstances
                raise OperationError("Input Conversation", "Translation", "Invalid Language of input file")
    return output


def translate_b_keyboard(in_string):
    """Translates the input from the Braille Keyboard into a string where each character represents a Braille Cell

    :param in_string: String or character to be translated
    :return: A list of the translated characters
    """
    out = []

    for char in in_string:
        out.append(b_keyboard_to_br[char])

    return out
