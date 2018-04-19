# tarlogger

Piece of code that reads 1-wire temperature sensor and wall-mounted presence button.
Temperature and button status are written in influxdb for stats and when presence changes, 
it is reported to Telegram and Slack.
