import colibricore

TMPDIR = "/tmp/" #this is where we'll store intermediate files

corpustext = """འབྲུག་པ་ ཀུན་ ལེགས་ ལ་ གསོལ་བ་ འདེབས་པ་
དུས་གསུམ་ རྒྱལ་བ་ འི་ ཡེ་ཤེས་ རྫུ་འཕྲུལ་ ག་
གདུལ་བྱ་ འི་ མགོན་ དུ་ ཤྲཱི་ ཧེ་རུ་ཀ་ འི་
རྣམ་པ་ ར་ རོལ་པ་ གྲུབ་པ་ འི་ སྤྱི་མེས་ མཆོག་
ཀུན་དགའ་ ལེགས་པ་ འི་ ཞབས་ ལ་ གསོལ་བ་ འདེབས་
གཟུང་འཛིན་ སྣང་བ་ ཆོས་ཉིད་ ཀློང་ གྲོལ་ ན་
བླ་མ་ ཁྱེད་ དང་ དབྱེ་ ར་ མེད་ བྱིན་ གྱིས་ རློབས་
ཐུབ་བསྟན་ ཆོ་ འཛིན་ གྱི་ བཞེད་ ངོ་ ར་ འཁྲུལ་ ཞིག་ བརྒྱད་ མིང་པ་ ས་ བྲིས་"""

corpusfile_plaintext = TMPDIR + "bo.txt"

with open(corpusfile_plaintext, 'w') as f: f.write(corpustext)

# Class encoding/decoding¶
# --------------------------

# Create Encoder
classfile = TMPDIR + "bo.colibri.cls"
classencoder = colibricore.ClassEncoder()
classencoder.build(corpusfile_plaintext)
classencoder.save(classfile)
print("Encoded ", len(classencoder), " classes, well done!")


# Encode Corpus
corpusfile = TMPDIR + "bo.colibri.dat" #this will be the encoded corpus file
classencoder.encodefile(corpusfile_plaintext, corpusfile)


# Decode the encoded corpus
classdecoder = colibricore.ClassDecoder(classfile)
decoded = classdecoder.decodefile(corpusfile)
print("Decoded Corpus")
print("---------------------------------")
print(decoded)


# Playing with Patterns
# --------------------------

#Build a pattern from a string, using the class encoder
p = classencoder.buildpattern("དུས་གསུམ་ རྒྱལ་བ་ འི་ ཡེ་ཤེས་ རྫུ་འཕྲུལ་ ག་")

#To print it we need the decoder
print("Print patterns")
print("---------------------------------")
print(p.tostring(classdecoder))
print(len(p))

print("Iterating over pattern tokens")
print("---------------------------------")
#Iterate over the token in a pattern, each token will be a Pattern instance
for token in p:
    print(token.tostring(classdecoder))


print("Extracting subpatterns by offset")
print("---------------------------------")
print(p[0].tostring(classdecoder))
print(p[-1].tostring(classdecoder))
print(p[2:4].tostring(classdecoder))


print("Bigram from patterns")
print("---------------------------------")
#let's get all bigrams
for ngram in p.ngrams(2):
    print(ngram.tostring(classdecoder))

print("All ngram from patterns")
print("---------------------------------")
#or all n-grams:
for ngram in p.ngrams():
    print(ngram.tostring(classdecoder))

print("or particular ngrams, such as unigrams up to trigrams:")
print("---------------------------------")
for ngram in p.ngrams(1,3):
    print(ngram.tostring(classdecoder))


print("The in operator can be used to check if a token OR ngram is part of a pattern")
print("---------------------------------")
#token
p2 = classencoder.buildpattern("རྒྱལ་བ་")
print(p2 in p)

#ngram
p3 = classencoder.buildpattern("རྒྱལ་བ་ འི་")
print(p3 in p)


print("Colibri Pattern is usually smaller than a string")
print("---------------------------------")
print(bytes(p), len(bytes(p)))
print(bytes("དུས་གསུམ་ རྒྱལ་བ་ འི་ ཡེ་ཤེས་ རྫུ་འཕྲུལ་ ག་".encode()), len(bytes("དུས་གསུམ་ རྒྱལ་བ་ འི་ ཡེ་ཤེས་ རྫུ་འཕྲུལ་ ག་".encode())))
print(len(bytes(p)) < len(bytes("དུས་གསུམ་ རྒྱལ་བ་ འི་ ཡེ་ཤེས་ རྫུ་འཕྲུལ་ ག་".encode())))
