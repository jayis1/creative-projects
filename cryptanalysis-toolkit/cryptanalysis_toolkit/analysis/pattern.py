"""Pattern word matching for cryptanalysis.

Matches cipher words against dictionary words by their letter pattern,
which is a powerful technique for breaking substitution ciphers.
"""

from __future__ import annotations
from typing import Dict, List, Optional


# Common English words organized by length for pattern matching
_COMMON_WORDS = {
    1: {"A", "I"},
    2: {"AN", "AT", "BE", "BY", "DO", "GO", "HE", "IF", "IN", "IS", "IT",
        "ME", "MY", "NO", "OF", "ON", "OR", "SO", "TO", "UP", "US", "WE"},
    3: {"ACE", "ACT", "ADD", "AGE", "AGO", "AID", "AIM", "AIR", "ALL", "AND",
        "ANY", "ARE", "ARK", "ARM", "ART", "ASK", "ATE", "BAD", "BAG", "BAN",
        "BAR", "BAT", "BED", "BIG", "BIT", "BOW", "BOX", "BOY", "BUT", "BUY",
        "CAN", "CAR", "CUP", "CUT", "DAD", "DAY", "DID", "DIG", "DOG", "DRY",
        "EAR", "EAT", "END", "EYE", "FAR", "FEW", "FIT", "FLY", "FOR", "FUN",
        "GAP", "GAS", "GOD", "GOT", "GUN", "HAD", "HAS", "HAT", "HER", "HIM",
        "HIS", "HIT", "HOT", "HOW", "ICE", "ILL", "ITS", "JAM", "JAR", "JET",
        "JOB", "KEY", "KID", "LAW", "LAY", "LET", "LIE", "LIP", "LOG", "LOT",
        "LOW", "MAN", "MAP", "MAY", "MIX", "NET", "NEW", "NIT", "NOT", "NOW",
        "NUT", "OAK", "ODD", "OFF", "OIL", "OLD", "ONE", "OUR", "OUT", "OWE",
        "OWN", "PAN", "PAT", "PAY", "PET", "PIN", "PIT", "PUT", "RAN", "RAT",
        "RAW", "RED", "RIB", "RIM", "ROW", "RUN", "SAD", "SAT", "SAW", "SAY",
        "SEA", "SET", "SHE", "SIT", "SIX", "SKY", "SON", "SUN", "TAP", "TAX",
        "TEA", "TEN", "THE", "TIE", "TIN", "TIP", "TOE", "TOP", "TOW", "TRY",
        "TUB", "TWO", "USE", "VAN", "VET", "WAR", "WAS", "WAY", "WET", "WHO",
        "WHY", "WIN", "WIT", "WON", "YET", "YOU"},
    4: {"ABLE", "ALSO", "AREA", "ARMY", "AWAY", "BABY", "BACK", "BALL", "BAND",
        "BANK", "BASE", "BATH", "BEAM", "BEAR", "BEAT", "BEEN", "BELL", "BEST",
        "BILL", "BIRD", "BITE", "BLOW", "BLUE", "BOAT", "BODY", "BOMB", "BOND",
        "BONE", "BOOK", "BOOT", "BORN", "BOSS", "BOTH", "BOWL", "BULK", "BURN",
        "BUSY", "CAFE", "CAGE", "CAKE", "CALL", "CALM", "CAME", "CAMP", "CARD",
        "CARE", "CASE", "CASH", "CAST", "CAVE", "CHAT", "CHIP", "CITY", "CLAP",
        "CLAY", "CLIP", "CLUB", "COAT", "CODE", "COLD", "COME", "COOK", "COOL",
        "COPE", "COPY", "CORD", "CORE", "CORN", "COST", "CREW", "CROP", "CURE",
        "CUTE", "DAMN", "DARE", "DARK", "DATA", "DATE", "DAWN", "DEAD", "DEAL",
        "DEAR", "DEBT", "DECK", "DEED", "DEEM", "DEEP", "DEER", "DENY", "DESK",
        "DIAL", "DIET", "DIRT", "DISH", "DISK", "DOOR", "DOSE", "DOWN", "DRAG",
        "DRAW", "DREW", "DROP", "DRUM", "DULL", "DUMB", "DUMP", "DUST", "DUTY",
        "EACH", "EARN", "EASE", "EAST", "EASY", "EDGE", "EDIT", "ELSE", "EMIT",
        "EVEN", "EVER", "EVIL", "EXAM", "EXEC", "EXIT", "FACE", "FACT", "FAIL",
        "FAIR", "FAKE", "FALL", "FAME", "FARM", "FAST", "FATE", "FEAR", "FEED",
        "FEEL", "FELL", "FELT", "FILE", "FILL", "FILM", "FIND", "FINE", "FIRE",
        "FIRM", "FISH", "FIST", "FLAG", "FLAT", "FLED", "FLEW", "FLIP", "FLOW",
        "FOAM", "FOLD", "FOLK", "FOND", "FOOD", "FOOL", "FOOT", "FORD", "FORE",
        "FORM", "FORT", "FOUL", "FOUR", "FREE", "FROM", "FUEL", "FULL", "FUND",
        "FURY", "FUSE", "GAIN", "GAME", "GANG", "GATE", "GAVE", "GAZE", "GEAR",
        "GENE", "GIFT", "GIRL", "GIVE", "GLAD", "GLOW", "GLUE", "GOAL", "GOES",
        "GOLD", "GOLF", "GONE", "GOOD", "GRAB", "GRAY", "GREW", "GREY", "GRIP",
        "GROW", "GULF", "GURU", "GUYS", "HAIR", "HALF", "HALL", "HALT", "HAND",
        "HANG", "HARD", "HARM", "HATE", "HAVE", "HEAD", "HEAL", "HEAP", "HEAR",
        "HEAT", "HEEL", "HELD", "HELL", "HELP", "HERE", "HERO", "HIGH", "HIKE",
        "HILL", "HINT", "HIRE", "HOLD", "HOLE", "HOME", "HOOK", "HOPE", "HOST",
        "HOUR", "HUGE", "HUNG", "HUNT", "HURT", "ICON", "IDEA", "INCH", "INTO",
        "IRON", "ITEM", "JACK", "JAIL", "JANE", "JEAN", "JOKE", "JUMP", "JUNE",
        "JURY", "JUST", "KEEN", "KEEP", "KEPT", "KICK", "KILL", "KIND", "KING",
        "KNEE", "KNEW", "KNIT", "KNOB", "KNOT", "KNOW", "LACK", "LAID", "LAKE",
        "LAMP", "LAND", "LANE", "LAST", "LATE", "LAWN", "LEAD", "LEAF", "LEAN",
        "LEFT", "LEND", "LENS", "LESS", "LICK", "LIFE", "LIFT", "LIKE", "LIMB",
        "LIME", "LINE", "LINK", "LION", "LIST", "LIVE", "LOAD", "LOAN", "LOCK",
        "LONG", "LOOK", "LORD", "LOSE", "LOSS", "LOST", "LOTS", "LOUD", "LOVE",
        "LUCK", "LUMP", "LUNG", "LURE", "LURK", "MADE", "MAIL", "MAIN", "MAKE",
        "MALE", "MALL", "MANY", "MARK", "MASS", "MATE", "MAYO", "MAZE", "MEAL",
        "MEAN", "MEAT", "MEET", "MELT", "MEMO", "MENU", "MERE", "MILD", "MILL",
        "MIND", "MINE", "MISS", "MODE", "MOOD", "MOON", "MORE", "MOSS", "MOST",
        "MOTH", "MOVE", "MUCH", "MUST", "MYTH", "NAIL", "NAME", "NAVY", "NEAT",
        "NECK", "NEED", "NEWS", "NEXT", "NICE", "NINE", "NODE", "NONE", "NOON",
        "NORM", "NOSE", "NOTE", "NOUN", "ODDS", "okay", "ONCE", "ONLY", "ONTO",
        "OPEN", "ORAL", "OURS", "OUTS", "OVEN", "OVER", "PACE", "PACK", "PAGE",
        "PAID", "PAIN", "PAIR", "PALE", "PALM", "PANE", "PARK", "PART", "PASS",
        "PAST", "PATH", "PEAK", "PEAR", "PEER", "PICK", "PILE", "PINE", "PINK",
        "PIPE", "PLAN", "PLAY", "PLEA", "PLOT", "PLOY", "PLUG", "PLUS", "POEM",
        "POET", "POLE", "POLL", "POND", "POOL", "POOR", "PORE", "PORT", "POSE",
        "POST", "POUR", "PRAY", "PREY", "PROP", "PULL", "PUMP", "PURE", "PUSH",
        "QUIT", "RACE", "RAGE", "RAID", "RAIL", "RAIN", "RANK", "RARE", "RATE",
        "READ", "REAL", "REAR", "RELY", "RENT", "REST", "RICH", "RIDE", "RING",
        "RISE", "RISK", "ROAD", "ROCK", "RODE", "ROLE", "ROLL", "ROOF", "ROOM",
        "ROOT", "ROPE", "ROSE", "RUIN", "RULE", "RUNG", "RUSH", "RUTH", "SACK",
        "SAFE", "SAGE", "SAID", "SAIL", "SAKE", "SALE", "SALT", "SAME", "SAND",
        "SANE", "SANG", "SAVE", "SEAL", "SEAM", "SEAT", "SECT", "SEED", "SEEK",
        "SEEM", "SEEN", "SELF", "SELL", "SEND", "SENT", "SHED", "SHIP", "SHOP",
        "SHOT", "SHOW", "SHUT", "SICK", "SIDE", "SIGH", "SIGN", "SILK", "SING",
        "SINK", "SITE", "SIZE", "SKIP", "SLAM", "SLAP", "SLID", "SLIM", "SLIP",
        "SLOT", "SLOW", "SNAP", "SNOW", "SOAK", "SOAP", "SOCK", "SOFT", "SOIL",
        "SOLD", "SOLE", "SOME", "SONG", "SOON", "SORT", "SOUL", "SOUR", "SPAN",
        "SPIN", "SPOT", "STAR", "STAY", "STEM", "STEP", "STIR", "STOP", "SUCH",
        "SUIT", "SURE", "SURF", "SWAP", "SWIM", "TAIL", "TAKE", "TALE", "TALK",
        "TALL", "TANK", "TAPE", "TASK", "TAXI", "TEAM", "TEAR", "TEEN", "TELL",
        "TEND", "TENT", "TERM", "TEST", "TEXT", "THAN", "THAT", "THEM", "THEN",
        "THEY", "THIN", "THIS", "THUS", "TIDE", "TIED", "TIER", "TILL", "TIME",
        "TINY", "TIRE", "TOLD", "TOLL", "TOMB", "TONE", "TOOK", "TOOL", "TOPS",
        "TORE", "TORN", "TOUR", "TOWN", "TRAP", "TREE", "TRIM", "TRIO", "TRIP",
        "TRUE", "TUBE", "TUCK", "TUNE", "TURN", "TWIN", "TYPE", "UGLY", "UNDO",
        "UNIT", "UPON", "URGE", "USED", "USER", "VAIN", "VALE", "VARY", "VAST",
        "VEIL", "VEIN", "VERB", "VERY", "VEST", "VICE", "VIEW", "VINE", "VISA",
        "VOID", "VOLT", "VOTE", "WADE", "WAGE", "WAIT", "WAKE", "WALK", "WALL",
        "WAND", "WANT", "WARD", "WARM", "WARN", "WARP", "WASH", "WAVE", "WEAK",
        "WEAR", "WEED", "WEEK", "WELL", "WENT", "WERE", "WEST", "WHAT", "WHEN",
        "WHOM", "WIDE", "WIFE", "WILD", "WILL", "WIND", "WINE", "WING", "WIRE",
        "WISE", "WISH", "WITH", "WOKE", "WOLF", "WOOD", "WOOL", "WORD", "WORE",
        "WORK", "WORM", "WORN", "WRAP", "YARD", "YARN", "YEAR", "YELL", "YOUR",
        "ZONE"},
}


def word_pattern(word: str) -> str:
    """Convert a word to its letter pattern.

    For example, 'HELLO' → '0.1.2.2.3' (each unique letter gets an
    incrementing number).

    Args:
        word: The word to patternize.

    Returns:
        Pattern string where each unique letter is mapped to a number.
    """
    pattern = []
    mapping: Dict[str, int] = {}
    next_id = 0
    for ch in word.upper():
        if ch not in mapping:
            mapping[ch] = next_id
            next_id += 1
        pattern.append(str(mapping[ch]))
    return ".".join(pattern)


class PatternMatcher:
    """Pattern word matching for cryptanalysis.

    Matches cipher words against dictionary words by their letter pattern,
    which is a powerful technique for breaking substitution ciphers.
    """

    def __init__(self, words: Optional[Dict[int, set]] = None) -> None:
        """Initialize with a word dictionary.

        Args:
            words: Dictionary mapping word length to set of words.
                   Uses built-in common English words if None.
        """
        self.words = words or _COMMON_WORDS
        self._pattern_index: Dict[int, Dict[str, List[str]]] = {}
        self._build_pattern_index()

    def _build_pattern_index(self) -> None:
        """Build an index mapping word patterns to matching words."""
        for length, word_set in self.words.items():
            self._pattern_index[length] = {}
            for word in word_set:
                pat = word_pattern(word)
                if pat not in self._pattern_index[length]:
                    self._pattern_index[length][pat] = []
                self._pattern_index[length][pat].append(word)

    def find_matches(self, cipher_word: str) -> List[str]:
        """Find dictionary words that match a cipher word's pattern.

        Args:
            cipher_word: A word from the ciphertext.

        Returns:
            List of possible plaintext words with matching patterns.
        """
        cipher_word = cipher_word.upper()
        length = len(cipher_word)
        if length not in self._pattern_index:
            return []
        pat = word_pattern(cipher_word)
        return self._pattern_index[length].get(pat, [])

    def get_pattern(self, word: str) -> str:
        """Get the letter pattern of a word.

        Args:
            word: The word to analyze.

        Returns:
            Pattern string like '0.1.2.2.3' for 'HELLO'.
        """
        return word_pattern(word)