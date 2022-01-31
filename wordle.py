import pickle as pkl
from time import time
import functools
import collections
import copy
import numpy as np


def get_wordlist(word_length = 5):
  with open('wordlist.txt', 'rt') as fp:
    all_words = fp.readlines()

  # Only wordles of size 5. Convert it to a tuple so it's hashable for the caching.
  all_words = tuple([word.strip().lower() for word in all_words if len(word.strip()) == word_length])
  return all_words

# Indirection that makes all inputs hashable so that caching works
def get_words_for_pattern(wordlist, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  if not isinstance(wordlist, collections.Hashable):
    raise Exception("wordlist must be hashable for caching")

  letters_with_wrong_pos_immutable = tuple([tuple(letters) for letters in letters_with_wrong_pos])
  return get_words_for_pattern_cached(wordlist, tuple(letters_with_pos), letters_with_wrong_pos_immutable, tuple(letters_not_in))

# Given a set of wordle answers find all possible words that fit the constraints.
@functools.lru_cache(maxsize=10000)
def get_words_for_pattern_cached(wordlist, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  matching_words = []
  for word in wordlist:
    skip_word = False

    # letters_not_in are all the letters we know are not part of the correct word
    for letter in letters_not_in:
      if letter in word:
        skip_word = True
        break
    if skip_word:
      continue

    # letters with pos are letters of which we know the correct answer (i.e. are green)
    for idx, letter in enumerate(letters_with_pos):
      if not letter.isalpha():
        continue
      if word[idx] != letter:
        skip_word = True
        break
    if skip_word:
      continue

    # letters_with_wrong_pos are letters that we know are part of the word but we only know where
    # they do not belong (i.e. yellow letters)
    for idx, letters in enumerate(letters_with_wrong_pos):
      for letter in letters:
        if letter not in word:
          skip_word = True
          break

        if word[idx] == letter:
          skip_word = True
          break
      if skip_word:
        break

    if skip_word:
      continue

    matching_words.append(word)
  return matching_words

# Indirection that makes all inputs hashable so that caching works
def count_words_for_pattern(wordlist, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  if not isinstance(wordlist, collections.Hashable):
    raise Exception("wordlist must be hashable for caching")

  letters_with_wrong_pos_immutable = tuple([tuple(letters) for letters in letters_with_wrong_pos])
  return count_words_for_pattern_cached(wordlist, tuple(letters_with_pos), letters_with_wrong_pos_immutable, tuple(letters_not_in))

# Same thing as get_words but only returns the counts, not the actual words. It's a slight and in hindsight
# pointless optimization for the search of the first guess.
@functools.lru_cache(maxsize=10000)
def count_words_for_pattern_cached(wordlist, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  matching_words = 0
  for word in wordlist:
    skip_word = False
    for letter in letters_not_in:
      if letter in word:
        skip_word = True
        break
    if skip_word:
      continue

    for idx, letter in enumerate(letters_with_pos):
      if not letter.isalpha():
        continue
      if word[idx] != letter:
        skip_word = True
        break
    if skip_word:
      continue

    for idx, letters in enumerate(letters_with_wrong_pos):
      for letter in letters:
        if letter not in word:
          skip_word = True
          break

        if word[idx] == letter:
          skip_word = True
          break
      if skip_word:
        break

    if skip_word:
      continue

    matching_words += 1
  return matching_words

# Given a word we guessed and knowing the correct word we update our knowledge about letters that are in the
# correct position, letters we know are part of the word but only know where they don't belong and letters
# we know are not part of the answer.
def add_wordle_reponse(guessed_word, correct_word, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  if len(guessed_word) != len(correct_word):
    raise Exception("Mismatching length of guess and correct_word")

  for idx, guess_letter in enumerate(guessed_word):
    if guess_letter == correct_word[idx]:
      letters_with_pos[idx] = guess_letter
      continue

    if guess_letter in correct_word:
      letters_with_wrong_pos[idx].add(guess_letter)
      continue

    letters_not_in.add(guess_letter)

  return letters_with_pos, letters_with_wrong_pos, letters_not_in

# The first word we guess will always be the same since we always have the same information. The strategy is as follows:
# If we guess a word e.g. "house" and the correct word is "hello" we get returned that "h" is in the correct position, "e"
# is part of the word but in the wrong position and none of the other letters are present. We don't know that hello is the
# answer but we can go through the dict and see how many words still remain viable candidates. Once we do this for all
# possible correct words, we get the average number of viable words for a specific guess. The optimal word to guess is one
# that minimizes the average number of viable words after the first guess. Turns out it's tares for a 5 letter word.
def find_optimal_first_word(wordlist, wordle_length):
  with open('average_num_remaining_words.pkl', 'rb') as fp:
    average_num_remaining_words = pkl.load(fp)

  for word_idx, guessed_word in enumerate(wordlist):
    if guessed_word in average_num_remaining_words:
      continue
    word_start_time = time()
    num_remaining_words = 0
    for correct_word in wordlist:
      letters_with_pos = [''] * wordle_length
      letters_with_wrong_pos = [set() for i in range(wordle_length)]
      letters_not_in = set()

      letters_with_pos, letters_with_wrong_pos, letters_not_in = add_wordle_reponse(guessed_word, correct_word, letters_with_pos, letters_with_wrong_pos, letters_not_in)
      num_remaining_words += count_words_for_pattern(wordlist, tuple(letters_with_pos), letters_with_wrong_pos, letters_not_in)

    average_num_remaining_words[guessed_word] = num_remaining_words / len(wordlist)
    with open('average_num_remaining_words.pkl', 'wb+') as fp:
      pkl.dump(average_num_remaining_words, fp)
    print("\n", guessed_word)
    print("Progress: ", word_idx, " of ", len(wordlist))
    print("Seconds since start: ", time() - start_time)
    print("Seconds for this word: ", time() - word_start_time)

  return sorted(average_num_remaining_words.items(), key=lambda item: item[1])[0][0]

# Find optimal guess is the iteration of what we did for the first word. Given some knowledge from previous guesses we 
# search for the guess that will minimize the average number words that are still possible after guessing the word.
def find_optimal_guess(wordlist, wordle_length, letters_with_pos, letters_with_wrong_pos, letters_not_in):
  matching_words = get_words_for_pattern(wordlist, letters_with_pos, letters_with_wrong_pos, letters_not_in)
  average_num_remaining_words = {}

  for guessed_word in matching_words:
    num_remaining_words = 0
    for correct_word in matching_words:
      new_letters_with_pos, new_letters_with_wrong_pos, new_letters_not_in = add_wordle_reponse(guessed_word, correct_word, copy.deepcopy(letters_with_pos), copy.deepcopy(letters_with_wrong_pos), copy.deepcopy(letters_not_in))
      num_remaining_words += count_words_for_pattern(wordlist, tuple(new_letters_with_pos), new_letters_with_wrong_pos, new_letters_not_in)
    average_num_remaining_words[guessed_word] = num_remaining_words / len(matching_words)
  return sorted(average_num_remaining_words.items(), key=lambda item: item[1])[0][0]

# Solving all possible words in the wordlist and return the paths of guessed words we took to get to them.
def solve_all_wordles(wordlist, worlde_length, first_word):
  # guess_path = {}
  # pkl.dump(guess_path, open('guess_paths.pkl', 'wb+'))
  # This loop runs a few hours even with caching, so better save snapshots
  with open('guess_paths.pkl', 'rb') as fp:
    guess_path = pkl.load(fp)

  # correct_word is the word we need to guess
  for correct_word in wordlist:
    word_start_time = time()
    if correct_word in guess_path:
      continue
    if correct_word == first_word:
      guess_path[correct_word] = first_word
      continue

    guesses = [first_word]
    letters_with_pos = [''] * wordle_length
    letters_with_wrong_pos = [set() for i in range(wordle_length)]
    letters_not_in = set()

    letters_with_pos, letters_with_wrong_pos, letters_not_in = add_wordle_reponse(first_word, correct_word, letters_with_pos, letters_with_wrong_pos, letters_not_in)

    while True:
      next_word = find_optimal_guess(wordlist, wordle_length, letters_with_pos, letters_with_wrong_pos, letters_not_in)
      guesses.append(next_word)
      letters_with_pos, letters_with_wrong_pos, letters_not_in = add_wordle_reponse(next_word, correct_word, letters_with_pos, letters_with_wrong_pos, letters_not_in)
      if ''.join(letters_with_pos) == correct_word:
        print('Found word ', correct_word, ' in ', len(guesses), ' took ', time()-word_start_time, 'seconds. steps:', guesses)
        break
    guess_path[correct_word] = guesses
    with open('guess_paths.pkl', 'wb') as fp:
      pkl.dump(guess_path, fp)

  return guess_path

if __name__ == "__main__":
  wordle_length = 5
  start_time = time()

  wordlist = get_wordlist()

  # First word is always the same (since we don't have any info) and takes the most time
  # so we do it once as a precomputation step.
  first_word = find_optimal_first_word(wordlist, wordle_length)

  # Use the startegy to solve all possible wordles to see how many we would fail.
  guess_paths = solve_all_wordles(wordlist, wordle_length, first_word)

  # Do some basic stats
  num_guesses = [len(guess_paths[word]) for word in guess_paths]
  print(f"Average number of guesses: {np.mean(num_guesses)}")
  print(f"Median number of guesses: {np.median(num_guesses)}")
  print(f"Number of words failed: {sum([1 for num in num_guesses if num >6])}")
  print(f"Fraction of words failed: {sum([1 for num in num_guesses if num >6]) / len(wordlist)}")
  worst_word = list(guess_paths)[num_guesses.index(max(num_guesses))]
  print(f"Worst word with {max(num_guesses)} guesses was {worst_word}")
  print(f"Guess paths of {worst_word} was {guess_paths[worst_word]}")