from flask import Flask, render_template, request
from difflib import SequenceMatcher
from textblob import TextBlob
from nltk.corpus import stopwords
from nltk import download
download('stopwords')

app = Flask(__name__)

####################### Sentence Semantic Similarity check ####################
import numpy as np # linear algebra
import math
import nltk
from nltk.corpus import wordnet as wn
from nltk import word_tokenize
from scipy import spatial
from nltk.metrics import edit_distance
from nltk.stem import PorterStemmer 
import re

ps = PorterStemmer()


def tokenize(q1, q2):
    """
        q1 and q2 are sentences/questions. Function returns a list of tokens for both.
    """
    return word_tokenize(q1), word_tokenize(q2)


def posTag(q1, q2):
    """
        q1 and q2 are lists. Function returns a list of POS tagged tokens for both.
    """
    return nltk.pos_tag(q1), nltk.pos_tag(q2)


def stemmer(tag_q1, tag_q2):
    """
        tag_q = tagged lists. Function returns a stemmed list.
    """

    stem_q1 = []
    stem_q2 = []

    for token in tag_q1:
        stem_q1.append(ps.stem(token))

    for token in tag_q2:
        stem_q2.append(ps.stem(token))

    return stem_q1, stem_q2

def path(set1, set2):
    return wn.path_similarity(set1, set2)


def wup(set1, set2):
    return wn.wup_similarity(set1, set2)


def edit(word1, word2):
    if float(edit_distance(word1, word2)) == 0.0:
        return 0.0
    return 1.0 / float(edit_distance(word1, word2))

class Lesk(object):

    def __init__(self, sentence):
        self.sentence = sentence
        self.meanings = {}
        for word in sentence:
            self.meanings[word] = ''

    def getSenses(self, word):
        # print word
        return wn.synsets(word.lower())

    def getGloss(self, senses):

        gloss = {}

        for sense in senses:
            gloss[sense.name()] = []

        for sense in senses:
            gloss[sense.name()] += word_tokenize(sense.definition())

        return gloss

    def getAll(self, word):
        senses = self.getSenses(word)

        if senses == []:
            return {word.lower(): senses}

        return self.getGloss(senses)

    def Score(self, set1, set2):
        # Base
        overlap = 0

        # Step
        for word in set1:
            if word in set2:
                overlap += 1

        return overlap

    def overlapScore(self, word1, word2):

        gloss_set1 = self.getAll(word1)
        if self.meanings[word2] == '':
            gloss_set2 = self.getAll(word2)
        else:
            # print 'here'
            gloss_set2 = self.getGloss([wn.synset(self.meanings[word2])])

        # print gloss_set2

        score = {}
        for i in gloss_set1.keys():
            score[i] = 0
            for j in gloss_set2.keys():
                score[i] += self.Score(gloss_set1[i], gloss_set2[j])

        bestSense = None
        max_score = 0
        for i in gloss_set1.keys():
            if score[i] > max_score:
                max_score = score[i]
                bestSense = i

        return bestSense, max_score

    def lesk(self, word, sentence):
        maxOverlap = 0
        context = sentence
        word_sense = []
        meaning = {}

        senses = self.getSenses(word)

        for sense in senses:
            meaning[sense.name()] = 0

        for word_context in context:
            if not word == word_context:
                score = self.overlapScore(word, word_context)
                if score[0] == None:
                    continue
                meaning[score[0]] += score[1]

        if senses == []:
            return word, None, None

        self.meanings[word] = max(meaning.keys(), key=lambda x: meaning[x])

        return word, self.meanings[word], wn.synset(self.meanings[word]).definition()

def computePath(q1, q2):

    R = np.zeros((len(q1), len(q2)))

    for i in range(len(q1)):
        for j in range(len(q2)):
            if q1[i][1] == None or q2[j][1] == None:
                sim = edit(q1[i][0], q2[j][0])
            else:
                sim = path(wn.synset(q1[i][1]), wn.synset(q2[j][1]))

            if sim == None:
                sim = edit(q1[i][0], q2[j][0])

            R[i, j] = sim

    # print R

    return R

def computeWup(q1, q2):

    R = np.zeros((len(q1), len(q2)))

    for i in range(len(q1)):
        for j in range(len(q2)):
            if q1[i][1] == None or q2[j][1] == None:
                sim = edit(q1[i][0], q2[j][0])
            else:
                sim = wup(wn.synset(q1[i][1]), wn.synset(q2[j][1]))

            if sim == None:
                sim = edit(q1[i][0], q2[j][0])

            R[i, j] = sim

    # print R

    return R

def overallSim(q1, q2, R):

    sum_X = 0.0
    sum_Y = 0.0

    for i in range(len(q1)):
        max_i = 0.0
        for j in range(len(q2)):
            if R[i, j] > max_i:
                max_i = R[i, j]
        sum_X += max_i

    for i in range(len(q1)):
        max_j = 0.0
        for j in range(len(q2)):
            if R[i, j] > max_j:
                max_j = R[i, j]
        sum_Y += max_j
        
    if (float(len(q1)) + float(len(q2))) == 0.0:
        return 0.0
        
    overall = (sum_X + sum_Y) / (2 * (float(len(q1)) + float(len(q2))))

    return overall

def semanticSimilarity(q1, q2):

    tokens_q1, tokens_q2 = tokenize(q1, q2)
    # stem_q1, stem_q2 = stemmer(tokens_q1, tokens_q2)
    tag_q1, tag_q2 = posTag(tokens_q1, tokens_q2)

    sentence = []
    for i, word in enumerate(tag_q1):
        if 'NN' in word[1] or 'JJ' in word[1] or 'VB' in word[1]:
            sentence.append(word[0])

    sense1 = Lesk(sentence)
    sentence1Means = []
    for word in sentence:
        sentence1Means.append(sense1.lesk(word, sentence))

    sentence = []
    for i, word in enumerate(tag_q2):
        if 'NN' in word[1] or 'JJ' in word[1] or 'VB' in word[1]:
            sentence.append(word[0])

    sense2 = Lesk(sentence)
    sentence2Means = []
    for word in sentence:
        sentence2Means.append(sense2.lesk(word, sentence))
    # for i, word in enumerate(sentence1Means):
    #     print sentence1Means[i][0], sentence2Means[i][0]

    R1 = computePath(sentence1Means, sentence2Means)
    R2 = computeWup(sentence1Means, sentence2Means)

    R = (R1 + R2) / 2

    # print R

    return overallSim(sentence1Means, sentence2Means, R)

### cleaning sentence ####
STOP_WORDS = nltk.corpus.stopwords.words()
def clean_sentence(val):
    "remove chars that are not letters or numbers, downcase, then remove stop words"
    regex = re.compile('([^\s\w]|_)+')
    sentence = regex.sub('', val).lower()
    sentence = sentence.split(" ")

    for word in list(sentence):
        if word in STOP_WORDS:
            sentence.remove(word)

    sentence = " ".join(sentence)
    return sentence

############ functions for similarity check ##################
# One word answer checker
def q1(given_ans, correct_ans):
    given_ans = given_ans.strip().lower()
    if SequenceMatcher(None, given_ans, correct_ans).ratio() < 0.49:
        return 0
    return SequenceMatcher(None, given_ans, correct_ans).ratio()

# Sentence answer checker
def q2(given_ans, correct_ans):
    # Firstly correcting spelling mistakes
    given_ans = TextBlob(given_ans).correct()
    given_ans = str(given_ans)
    given_ans = clean_sentence(given_ans)
    score = semanticSimilarity(correct_ans, given_ans)
    if score < 0.3:
        return 0
    return score*2

######## routing of urls #############


@app.route('/')
def index():
    return render_template("index.html")

arr = """an array data structure, or simply an array, is a data structure consisting of a collection of elements, 
each identified by at least one array index or key."""

@app.route('/results/', methods=["GET", "POST"])
def show_results():
    ans1 = request.form["first"]
    ans2 = request.form["second"]
    s1 = q1(ans1,"stack")
    s2 = q2(ans2,arr)
    s2 = s2*3
    s1 = s1*2
    s2 = round(s2,3)
    s1 = round(s1,3)
    return render_template("marks.html", ans1=ans1,s1=s1, ans2=ans2,s2=s2,tot = round((s1+s2),3))

if __name__ == "__main__":
    app.run()
