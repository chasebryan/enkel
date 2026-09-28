"""Closed, versioned vocabulary. No guessed English inflections."""
from dataclasses import asdict, dataclass
import hashlib
import json

ROLES = ("se", "ob", "to", "vi", "at", "on")
VERSION = "0.2.0"


@dataclass(frozen=True)
class Noun:
    singular: str
    plural: str
    count: bool = True
    human: bool = False


@dataclass(frozen=True)
class Verb:
    third: str
    past: str
    participle: str
    progressive: str
    required: tuple[str, ...]
    permitted: tuple[str, ...]


NOUNS = {
    "world": Noun("world", "worlds"),
    "speaker": Noun("speaker", "speakers", human=True),
    "listener": Noun("listener", "listeners", human=True),
    "cat": Noun("cat", "cats"),
    "dog": Noun("dog", "dogs"),
    "child": Noun("child", "children", human=True),
    "teacher": Noun("teacher", "teachers", human=True),
    "student": Noun("student", "students", human=True),
    "person": Noun("person", "people", human=True),
    "man": Noun("man", "men", human=True),
    "woman": Noun("woman", "women", human=True),
    "friend": Noun("friend", "friends", human=True),
    "cookie": Noun("cookie", "cookies"),
    "book": Noun("book", "books"),
    "picture": Noun("picture", "pictures"),
    "telescope": Noun("telescope", "telescopes"),
    "room": Noun("room", "rooms"),
    "house": Noun("house", "houses"),
    "park": Noun("park", "parks"),
    "day": Noun("day", "days"),
    "night": Noun("night", "nights"),
    "hour": Noun("hour", "hours"),
    "apple": Noun("apple", "apples"),
    "idea": Noun("idea", "ideas"),
    "robot": Noun("robot", "robots"),
    "mouse": Noun("mouse", "mice"),
    "key": Noun("key", "keys"),
    "door": Noun("door", "doors"),
    "water": Noun("water", "", count=False),
    "music": Noun("music", "", count=False),
}


def _v(third, past, participle, progressive, required=("se",), objects=()):
    return Verb(third, past, participle, progressive, required,
                ("se",) + tuple(objects) + ("vi", "at", "on"))


VERBS = {
    "greet": _v("greets", "greeted", "greeted", "greeting", ("se", "ob"), ("ob",)),
    "eat": _v("eats", "ate", "eaten", "eating", objects=("ob",)),
    "see": _v("sees", "saw", "seen", "seeing", ("se", "ob"), ("ob",)),
    "hold": _v("holds", "held", "held", "holding", ("se", "ob"), ("ob",)),
    "give": _v("gives", "gave", "given", "giving", ("se", "ob", "to"), ("ob", "to")),
    "show": _v("shows", "showed", "shown", "showing", ("se", "ob", "to"), ("ob", "to")),
    "read": _v("reads", "read", "read", "reading", objects=("ob",)),
    "write": _v("writes", "wrote", "written", "writing", objects=("ob", "to")),
    "sleep": _v("sleeps", "slept", "slept", "sleeping"),
    "walk": _v("walks", "walked", "walked", "walking"),
    "run": _v("runs", "ran", "run", "running"),
    "arrive": _v("arrives", "arrived", "arrived", "arriving"),
    "leave": _v("leaves", "left", "left", "leaving", objects=("ob",)),
    "like": _v("likes", "liked", "liked", "liking", ("se", "ob"), ("ob",)),
    "love": _v("loves", "loved", "loved", "loving", ("se", "ob"), ("ob",)),
    "chase": _v("chases", "chased", "chased", "chasing", ("se", "ob"), ("ob",)),
    "help": _v("helps", "helped", "helped", "helping", ("se", "ob"), ("ob",)),
    "know": _v("knows", "knew", "known", "knowing", ("se", "ob"), ("ob",)),
    "open": _v("opens", "opened", "opened", "opening", objects=("ob",)),
    "close": _v("closes", "closed", "closed", "closing", objects=("ob",)),
    "drink": _v("drinks", "drank", "drunk", "drinking", objects=("ob",)),
    "flow": _v("flows", "flowed", "flowed", "flowing"),
    "work": _v("works", "worked", "worked", "working"),
}

ADJECTIVES = frozenset(("red", "blue", "green", "black", "white", "small", "large",
                        "young", "old", "quiet", "happy", "sad", "open", "closed",
                        "round", "bright", "empty", "full"))


def description():
    return {"version": VERSION,
            "nouns": {k: asdict(v) for k, v in sorted(NOUNS.items())},
            "verbs": {k: asdict(v) for k, v in sorted(VERBS.items())},
            "adjectives": sorted(ADJECTIVES)}


def digest():
    data = json.dumps(description(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode()).hexdigest()
