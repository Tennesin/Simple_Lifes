import gc
from game import Game

if __name__ == "__main__":
    game = Game()
    gc.freeze()

    game.run()