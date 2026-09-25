# IF scene in the fixtures' style, written to be spec-clean (hazards are in doc01b / probes).
SOURCE = '''include:
  - foyer
  - cellar

given:
  - Lamp = 1
  - Seen Cellar = 0

cellar:

  - when:
      - Location = "Cellar"
      - Lamp >= 1

  - The cellar smells of damp stone -- and something worse. Note: the door is locked.
    A sign reads "KEEP OUT: 3:1 odds you regret it." (Someone's idea of a joke.)

  - Note: the door is locked.

  - [Try the door.]{Strength > 2}It doesn't budge -- not even a little.

  - choice:

      - [Check your watch.]It is 12:30 exactly. The ratio of rats to lamps is 3:1.

      - [Read the pamphlet.]The pamphlet says to visit http://example.com/cellar for details.
        ...

      - {Lamp == 0}[Feel along the wall.]'Anyone there?' you whisper.

  - effect:
      - Lamp -= 1
      - Seen Cellar = 1
'''
_cellar = [
    {'when': ['Location = "Cellar"', 'Lamp >= 1']},
    'The cellar smells of damp stone -- and something worse. Note: the door is locked.\n'
    'A sign reads "KEEP OUT: 3:1 odds you regret it." (Someone\'s idea of a joke.)',
    'Note: the door is locked.',
    "[Try the door.]{Strength > 2}It doesn't budge -- not even a little.",
    {'choice': [
        '[Check your watch.]It is 12:30 exactly. The ratio of rats to lamps is 3:1.',
        '[Read the pamphlet.]The pamphlet says to visit http://example.com/cellar for details.\n...',
        "{Lamp == 0}[Feel along the wall.]'Anyone there?' you whisper.",
    ]},
    {'effect': ['Lamp -= 1', 'Seen Cellar = 1']},
]
SPEC = {'include': ['foyer', 'cellar'], 'given': ['Lamp = 1', 'Seen Cellar = 0'], 'cellar': _cellar}
AUTHOR = SPEC
