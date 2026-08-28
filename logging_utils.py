from datetime import datetime
import atexit

import data_loading_utils as dlus


class Logger:
    def __init__(self, name, to_file=False):
        self.name = name
        self.to_file = to_file
        self.time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.body = []

        atexit.register(self.exit)

    def add(self, content):
        self.body.append(content)

    def exit(self):
        if len(self.body) == 0:
            return

        joined_body = ''.join(self.body) + f'>>>>> end {self.name} <<<<<\n\n'

        last_log_path = 'logs/' + self.name + '_last'

        try:
            if (
                dlus.file_to_str(last_log_path).split('\n', 1)[1]
                == joined_body
            ):
                return

        except FileNotFoundError:
            pass

        joined_body = (
            f'>>>>> {self.name} [{self.time}] <<<<<\n'
            + joined_body
        )

        if self.to_file:
            dlus.str_to_file(joined_body, 'logs/' + self.name, append=True)
        else:
            print(joined_body, end='')

        dlus.str_to_file(joined_body, last_log_path)


if __name__ == '__main__':
    logger = Logger('logging_utils')
    logger.add('differen stuff\n')
    logger.add('some more different stuff\n')
