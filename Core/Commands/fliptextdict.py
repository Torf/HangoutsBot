fliptextdict = {
 '!': '\u00a1',
 "'": ',',
 '(': ')',
 '.': '\u02d9',
 '6': '9',
 ';': '\u061b',
 '?': '\u00bf',
 'A': '\u2200',
 'B': '\U00010412',
 'C': '\u03fd',
 'D': '\u15e1',
 'E': '\u018e',
 'F': '\u2132',
 'G': '\u2141',
 'H': 'H',
 'I': 'I',
 'J': '\u017f',
 'K': '\u029e',
 'L': '\u2142',
 'M': 'W',
 'N': 'N',
 'O': 'O',
 'P': '\u0500',
 'Q': '\u1f49',
 'R': '\u1d1a',
 'S': 'S',
 'T': '\u22a5',
 'U': '\u2229',
 'V': '\u039b',
 'W': 'M',
 'X': 'X',
 'Y': '\u028e',
 'Z': 'Z',
 '[': ']',
 '_': '\u203e',
 'a': '\u0250',
 'b': 'q',
 'c': '\u0254',
 'd': 'p',
 'e': '\u01dd',
 'f': '\u025f',
 'g': '\u0183',
 'h': '\u0265',
 'i': '\u0131',
 'j': '\u027e',
 'k': '\u029e',
 'l': '\u05df',
 'm': '\u026f',
 'n': 'u',
 'o': 'o',
 'p': 'd',
 'q': 'b',
 'r': '\u0279',
 's': 's',
 't': '\u0287',
 'u': 'n',
 'v': '\u028c',
 'w': '\u028d',
 'x': 'x',
 'y': '\u028e',
 'z': 'z',
 '{': '}'
}

# add the reverse of every entry to make it symmetrical
fliptextdict.update({v: k for k, v in fliptextdict.items()})
