from flask import Flask, render_template, request, session
from flask import redirect, url_for, jsonify
import redis

app = Flask(__name__)
app.secret_key = 'not_secret_at_all'

r = redis.StrictRedis(host='localhost', port=6379, db=0)


@app.route('/create_board', methods=['POST'])
def create_board():
    """Endpoint user for creating the starting boards.

    Player 1 will post to this route with a unique game identifier and their created board. After the game is created,
    the unique game number can be provided to player 2, allowing them to then post their own board. Players will then
    call polling until it is their own turn.

    Params:
        gameNum: A unique game identifier.
        playerNum: The player who is posting their board.
        board: The player's board.

    Returns:
        A JSON object containing informing whose board was created.
        Example:

        {
          "msg": "Created board for player 1",
          "success": 1
        }
    """
    resp_dict = {}
    if int(request.form['playerNum']) == 1:
        # TODO Create gameNum key and insert board info for player 1
        r.hset(str(request.form['gameNum']), 'gameNum', int(request.form['gameNum']))
        r.hset(str(request.form['gameNum']), 'player1_board', request.form['board'])
        r.hset(str(request.form['gameNum']), 'player1_board_p2', '0' * 64)
        resp_dict['success'] = 1
        resp_dict['msg'] = 'Created board for player 1'
        return jsonify(**resp_dict)
    else:
        # TODO Access existing gameNum and insert board info for player 2
        if not (r.hget(str(request.form['gameNum']), 'gameNum')):
            resp_dict['success'] = 0
            resp_dict['msg'] = "Game does not exist"
            return jsonify(**resp_dict)
        r.hset(str(request.form['gameNum']), 'player2_board', request.form['board'])
        r.hset(str(request.form['gameNum']), 'player2_board_p1', '0' * 64)
        r.hset(str(request.form['gameNum']), 'whose_turn', 1)
        resp_dict['success'] = 1
        resp_dict['msg'] = 'Created board for player 2'
        return jsonify(**resp_dict)

@app.route('/polling', methods=['POST'])
def polling():
    """Endpoint used for updating a player when there turn is

    Players will call polling once every second until a JSON object is returned containing board information, meaning
    it is now the polling user's turn.

    Params:
        gameNum: The current game number.
        playerNum: The player who is current polling.

    Returns:
        A JSON object specifying all the current board information. 'msg' will be 'You lose' if the player lost.
        Example:

        {
          "msg": "Go",
          "player1_board": "1111000000000000000000000000000000000000000000000000000000000000",
          "player1_board_p2": "0000000000000000000000000000000000000000000000000000000000000000",
          "player2_board": "1111000000000000000000000000000000000000000000000000000000000000",
          "player2_board_p1": "0000000000000000000000000000000000000000000000000000000000000000",
          "success": 1
        }
    """
    whose_turn = int(r.hget(str(request.form['gameNum']), 'whose_turn'))
    resp_dict = {}
    if whose_turn == 0:
        resp_dict['success'] = 1
        resp_dict['msg'] = 'You lose'
        return jsonify(**resp_dict)
    if whose_turn == int(request.form['playerNum']):
        # opp_board_name = ''
        # if whose_turn == 1:
        #     opp_board_name = 'player2_board'
        # else:
        #     opp_board_name = 'player1_board'
        resp_dict['player1_board'] = str(r.hget(str(request.form['gameNum']), 'player1_board'), 'utf-8')
        resp_dict['player2_board'] = str(r.hget(str(request.form['gameNum']), 'player2_board'), 'utf-8')
        resp_dict['player1_board_p2'] = str(r.hget(str(request.form['gameNum']), 'player1_board_p2'), 'utf-8')
        resp_dict['player2_board_p1'] = str(r.hget(str(request.form['gameNum']), 'player2_board_p1'), 'utf-8')
        resp_dict['success'] = 1
        resp_dict['msg'] = 'Go'
        return jsonify(**resp_dict)
    else:
        resp_dict['success'] = 0
        resp_dict['msg'] = "Don't go"
        return jsonify(**resp_dict)

@app.route('/fire', methods=['POST'])
def fire():
    """Process firing at the opponent.

    Checks if it's the player's turn, and if correct continues to process the shot, updating the board they see
    and the opponents actual board.

    Params:
        gameNum: The current game number.
        playerNum: The player who is firing.
        x: The x coordinate (column) the user is firing at.
        y: The y coordinate (row) the user is firing at.

    Returns:
        A JSON object containing the current board the person firing can see of their opponent, and whether or not they
        hit. 'msg' will be 'You win' if there are no more ships alive for the opponent.
        Example:
        {
          "board_seen": "0200000000000000000000000000000000000000000000000000000000000000",
          "msg": "Hit",
          "success": 1
        }
    """

    resp_dict = {}
    whose_turn = int(r.hget(str(request.form['gameNum']), 'whose_turn'))
    if whose_turn != int(request.form['playerNum']):
        resp_dict['success'] = 0
        resp_dict['msg'] = "Not your turn"
        return jsonify(**resp_dict)
    board_to_fire_at_str = ''
    board_seen_name_str = ''
    if whose_turn == 1:
        whose_turn = 2
        board_to_fire_at_str = 'player2_board'
        board_seen_name_str = 'player1_board_p2'
    else:
        whose_turn = 1
        board_to_fire_at_str = 'player1_board'
        board_seen_name_str = 'player2_board_p1'
    index = int(request.form['y']) * 8 + int(request.form['x'])
    board = list(str(r.hget(str(request.form['gameNum']), board_to_fire_at_str), 'utf-8'))
    board_seen = list(str(r.hget(str(request.form['gameNum']), board_seen_name_str), 'utf-8'))
    # Miss
    if board[index] == '0':
        board[index] = '3'
        board_seen[index] = '3'
        resp_dict['msg'] = 'Miss'
    # Hit
    if board[index] == '1':
        board[index] = '2'
        board_seen[index] = '2'
        resp_dict['msg'] = 'Hit'
    board_str = ''.join(board)
    board_seen_str = ''.join(board_seen)
    resp_dict['board_seen'] = board_seen_str
    r.hset(str(request.form['gameNum']), board_to_fire_at_str, board_str)
    r.hset(str(request.form['gameNum']), board_seen_name_str, board_seen_str)
    resp_dict['success'] = 1

    # If no more parts of a ship are without hits, the firing player wins
    # Set turn to 0 so the polling user knows they lost
    if board_str.find('1') == -1:
        resp_dict['msg'] = 'You win'
        r.hset(str(request.form['gameNum']), 'whose_turn', 0)
    else:
        r.hset(str(request.form['gameNum']), 'whose_turn', whose_turn)
    return jsonify(**resp_dict)

if __name__ == '__main__':
    app.debug = True
    app.run("0.0.0.0", port=5000)