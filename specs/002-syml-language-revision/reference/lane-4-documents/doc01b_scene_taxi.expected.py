# IF scene the way an author actually types it: capitalized top key (as in the stranger fixture),
# a paragraph break inside one beat, a prose dash line, quoted dialogue whose first word is
# lowercase + colon, an ellipsis-led line with a colon.
SOURCE = '''Given:
  - Money = 5

taxi:

  - The cab smelled like wet dog and cheap cigars. The meter read 3:15.

    Rain, rain -- always rain.

  - "Where to?" the driver asked. I told him: the docks.

  - choice: "The docks," I said.

  - choice:

      - [Pay the fare.]

      - {Money >= 5}You hand over five bucks -- he doesn't count it.
        - and that's that.

  - "...and then: nothing," he muttered.
'''
# Spec prediction: `Given:` has an uppercase letter -> root TextLeaf "Given:"; the next line
# `  - Money = 5` is a ListItem that a TextLeaf cannot accept -> OutOfContextNodeError on line 2.
SPEC = ('error', 'OutOfContextNodeError')
AUTHOR = {
    'Given': ['Money = 5'],
    'taxi': [
        'The cab smelled like wet dog and cheap cigars. The meter read 3:15.\n\nRain, rain -- always rain.',
        '"Where to?" the driver asked. I told him: the docks.',
        {'choice': '"The docks," I said.'},
        {'choice': ['[Pay the fare.]', "{Money >= 5}You hand over five bucks -- he doesn't count it.\n- and that's that."]},
        '"...and then: nothing," he muttered.',
    ],
}
