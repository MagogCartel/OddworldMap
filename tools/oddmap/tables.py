"""Static game data: the level lists the build walks, and the name tables the
discs do not carry."""

# (LevelId, short, display), listed in game progression order
# (id is the game's LevelIds enum value; the list order drives the viewer UI)
AO_LEVELS = [
    (1, "R1", "Rupture Farms"),
    (5, "E1", "Stock Yards"),
    (2, "L1", "Monsaic Lines"),
    (3, "F1", "Paramonia"),
    (4, "F2", "Paramonian Temple"),
    (14, "F4", "Paramonia Escape"),
    (8, "D1", "Scrabania"),
    (9, "D2", "Scrabanian Temple"),
    (15, "D7", "Scrabania Escape"),
    (6, "E2", "Stock Yards Return"),
    (13, "R2", "Rupture Farms Return"),
    (12, "R6", "Board Room"),
    (10, "C1", "Credits"),
    (0, "S1", "Menu"),
]

# Rescue Zulag membership of Rupture Farms Return paths: the game names R2
# save slots "Rescue Zulag N" by finding the current path id in this table
# (AliveLibAO/SaveGame.cpp word_4BC670, applied via PauseMenu's gLevelNames)
AO_R2_ZULAGS = {
    1: (15, 16, 17, 18, 19, 20),
    2: (1, 2, 3, 10),
    3: (5, 7, 9, 12, 13),
    4: (4, 8, 11, 14),
}

AO_TLV_NAMES = {
    0:"ContinuePoint",1:"PathTransition",2:"ContinueZone",3:"Hoist",4:"Edge",5:"DeathDrop",6:"Door",
    7:"ShadowZone",8:"LiftPoint",11:"WellLocal",12:"Dove",13:"RockSack",14:"ZBall",15:"FallingItem",
    18:"PullRingRope",19:"BackgroundAnimation",20:"Honey",22:"TimedMine",24:"Slig",25:"Slog",
    26:"Switch",27:"BellHammer",28:"StartController",29:"SecurityOrb",32:"LiftMudokon",
    34:"BeeSwarmHole",35:"Pulley",36:"HoneySack",37:"AbeStart",38:"ElumStart",40:"ElumWall",
    41:"SlingMudokon",42:"HoneyDripTarget",43:"Bees",45:"WellExpress",46:"Mine",47:"UXB",
    48:"Paramite",49:"Bat",50:"RingMudokon",51:"MovieStone",52:"BirdPortal",53:"BirdPortalExit",
    54:"BellSongStone",55:"TrapDoor",56:"RollingBall",57:"SligBoundLeft",58:"InvisibleZone",
    59:"RollingBallStopper",60:"FootSwitch",61:"SecurityClaw",62:"MotionDetector",66:"SligSpawner",
    67:"ElectricWall",68:"LiftMover",69:"ChimeLock",71:"MeatSack",72:"Scrab",73:"FlintLockFire",
    74:"ScrabLeftBound",75:"ScrabRightBound",76:"SligBoundRight",77:"SligPersist",79:"EnemyStopper",
    81:"InvisibleSwitch",82:"Mudokon",83:"ZSligCover",84:"DoorFlame",86:"MovingBomb",
    87:"MovingBombStopper",88:"MeatSaw",89:"MudokonPathTrans",90:"MenuController",92:"HintFly",
    93:"ScrabNoFall",94:"IdSplitter",95:"SecurityDoor",96:"DemoPlaybackStone",97:"BoomMachine",
    98:"LCDScreen",99:"ElumPathTrans",100:"HandStone",101:"CreditsController",102:"Preloader",
    103:"LCDStatusBoard",105:"MusicTrigger",106:"LightEffect",107:"SlogSpawner",108:"DeathClock",
    109:"RingCancel",110:"GasEmitter",111:"SlogHut",112:"Glukkon",113:"KillUnsavedMuds",
    114:"SoftLanding",115:"ResetPath",
}

AE_LEVEL_DISPLAY = {
    0: "Menu", 1: "Necrum Mines", 2: "Necrum", 3: "Mudomo Vault", 4: "Mudanchee Vault",
    5: "FeeCo Depot", 6: "Slig Barracks", 7: "Mudanchee Vault Ender", 8: "Bonewerkz",
    9: "SoulStorm Brewery", 10: "Brewery Ender", 11: "Mudomo Vault Ender",
    12: "FeeCo Depot Ender", 13: "Barracks Ender", 14: "Bonewerkz Ender",
    15: "Test Level", 16: "Credits",
}
# base levels followed by their enders, mirroring the playthrough
AE_LEVEL_ORDER = [1, 2, 3, 11, 4, 7, 5, 12, 6, 13, 8, 14, 9, 10, 16, 0, 15]
