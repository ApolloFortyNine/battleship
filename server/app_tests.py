from app import app
import unittest
import random
import redis


class AppTestCase(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.r = redis.StrictRedis(host='localhost', port=6379, db=0)
        self.board1 = "11100000" + ("0" * 58)
        self.board2 = "00000111" + ("0" * 58)
        self.number = random.randint(0,1000000000)

    def create_board(self, board, gameNum, playerNum):
        return self.app.post('/create_board', data=dict(
            board=board,
            gameNum=gameNum,
            playerNum=playerNum
        ))

    def polling(self, gameNum, playerNum):
        return self.app.post('/polling', data=dict(
            gameNum=gameNum,
            playerNum=playerNum
        ))

    def fire(self, gameNum, playerNum, x, y):
        return self.app.post('/fire', data=dict(
            gameNum=gameNum,
            playerNum=playerNum,
            x=x,
            y=y
        ))

    def test_create_board(self):
        result = self.create_board(self.board1, self.number, 1)
        self.assertIn("Created board for player 1", str(result.data, 'utf-8'))
        result = self.create_board(self.board2, self.number, 2)
        self.assertIn("Created board for player 2", str(result.data, 'utf-8'))
        self.assertEqual(int(self.r.hget(str(self.number), 'whose_turn')), 1, msg="Should be player 1's turn")

    def test_polling(self):
        self.create_board(self.board1, self.number, 1)
        self.create_board(self.board2, self.number, 2)
        result = self.polling(self.number, 2)
        self.assertIn("Don't go", str(result.data, 'utf-8'))
        result = self.polling(self.number, 1)
        self.assertIn("player1_board", str(result.data, 'utf-8'))

    def test_fire_miss(self):
        self.create_board(self.board1, self.number, 1)
        self.create_board(self.board2, self.number, 2)
        self.polling(self.number, 1)
        result = self.fire(self.number, 1, 7, 7)
        self.assertIn("Miss", str(result.data, 'utf-8'))

    def test_fire_hit(self):
        self.create_board(self.board1, self.number, 1)
        self.create_board(self.board2, self.number, 2)
        self.polling(self.number, 1)
        result = self.fire(self.number, 1, 7, 0)
        self.assertIn("Hit", str(result.data, 'utf-8'))

    def test_fire_wrong_player(self):
        self.create_board(self.board1, self.number, 1)
        self.create_board(self.board2, self.number, 2)
        self.polling(self.number, 1)
        result = self.fire(self.number, 2, 7, 0)
        self.assertIn("Not your turn", str(result.data, 'utf-8'))

    def test_game_does_not_exist(self):
        result = self.create_board(self.board2, self.number, 2)
        self.assertIn("Game does not exist", str(result.data, 'utf-8'))

    def test_full_game(self):
        self.create_board(self.board1, self.number, 1)
        self.create_board(self.board2, self.number, 2)
        self.polling(self.number, 1)
        self.fire(self.number, 1, 7, 0)
        self.polling(self.number, 1)
        self.polling(self.number, 2)
        self.fire(self.number, 2, 7, 3)
        self.polling(self.number, 1)
        self.polling(self.number, 2)
        self.fire(self.number, 1, 6, 0)
        self.polling(self.number, 2)
        self.polling(self.number, 1)
        self.fire(self.number, 2, 6, 3)
        self.polling(self.number, 2)
        self.polling(self.number, 1)
        result = self.fire(self.number, 1, 5, 0)
        self.assertIn("You win", str(result.data, 'utf-8'), self.number)
        result = self.polling(self.number, 2)
        self.assertIn("You lose", str(result.data, 'utf-8'))


if __name__ == '__main__':
    unittest.main()
