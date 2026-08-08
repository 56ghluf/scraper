from datetime import datetime
import atexit

import data_loading_utils as dlus


class Logger:
    def __init__(self, name):
        self.name = name
        self.time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.body = []

        atexit.register(self.exit)

    def add(self, content):
        self.body.append(content)

    def exit(self):
        if len(self.body) == 0:
            return

        joined_body = ''.join(self.body)

        try:
            if (
                dlus.file_to_str('logs/' + self.name).split('\n', 1)[1] 
                == joined_body
            ):
                return

        except FileNotFoundError:
            pass

        joined_body = f'===== {self.name} [{self.time}] =====\n' + joined_body
        print(joined_body, end='')

        dlus.str_to_file(joined_body, 'logs/' + self.name)


if __name__ == '__main__':
    logger = Logger('logging_utils')
    logger.add('different stuff\n')
    logger.add('some more different stuff\n')
