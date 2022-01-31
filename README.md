# Wordle Solver
The first word we guess will always be the same since we always have the same information. The strategy is as follows:
If we guess a word e.g. "house" and the correct word is "hello" we get returned that "h" is in the correct position, "e"
is part of the word but in the wrong position and none of the other letters are present. We don't know that hello is the
answer but we can go through the dict and see how many words still remain viable candidates. Once we do this for all
possible correct words, we get the average number of viable words for a specific guess. The optimal word to guess is one
that minimizes the average number of viable words after the first guess. Turns out it's tares for a 5 letter word.

## First word

Turns out the best first guess for the wordlist here is "tares"

## Statistics

