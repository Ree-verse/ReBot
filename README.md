#  Incomplete project, still in progress (nearly all of the work completed to date was done at the end of August): As shown below, very few features are currently implemented. 
*(This project was primarily intended to help me become familiar with and learn how to develop Discord bots.)*

## To do

- [ ] Server leaderboard: award 1 XP when a member sends a message in the binary counting channel, 0.1 XP in the spam channel, 5 XP in the feedback or general channels, and 3 XP in any other channel. Also implement related commands, such as `leaderboard`, `xp` (with `add` and `remove` options), and `user_level`
- [ ] `tic_tac_toe` game command with options such as `multiplayer` and `solo`
- [ ] Utility commands: `generate_pwd` (with various options), `rotate_picture` (with options such as speed and direction), `generate_pseudo` (based on the options already available in [pseudo-generator](https://github.com/Ree-verse/pseudo-generator)), `translate`, `user_infos`, `server_infos`, `youtube` (with `search` and `infos` options), `ping`, and `whois`
- [ ] Message logging: log deleted and edited messages in a dedicated channel for moderators
- [ ] Ticket management: implement a `ticket` (available for moderators only) command with `reopen`, `create`, `delete`, `close` options, using a dedicated category for their reception
- [ ] `clear` command: allow moderators to delete a specified number of the most recent messages, with an optional filter to target messages sent by a specific user
- [ ] Security features: detect and handle spam, compromised moderator accounts (which could potentially delete large numbers of messages or channels, or perform other destructive actions within minutes), mass mentions, and other threats
- [ ] Warning system: implement a `warn` command with `list`, `remove`, and `add` options
- [ ] Automatic bump reminder system: remind users to bump every two hours
- [ ] `help` command: display all the bot's features
- [ ] `runpy` command: allow moderators to execute Python code in a specific channel
- [ ] `set_count` command: allow moderators to set the initial count for the binary counting channel
- [ ] Maybe also add some casino features like `/work` or `/roulette` in the future, similar to [UnbelievaBoat](https://unbelievaboat.com)

## Code note

Certain functions and variables are intentionally only used once, for readability purposes.

## Credits

This project was (very) inspired by IdefaBot and [devcord-bot](https://github.com/idefasoft/devcord-bot).  
Many thanks to Idefa for the inspiration.

## License

[MIT License](LICENSE) © 2026 Ree-verse
