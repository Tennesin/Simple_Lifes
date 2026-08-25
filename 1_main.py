import gc
from game import Game

if __name__ == "__main__":
    gc.set_threshold(50000, 25, 25)
    game = Game()
    gc.freeze()

    game.run()