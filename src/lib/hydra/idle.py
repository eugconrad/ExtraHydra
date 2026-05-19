import time


class IdleManager:
    def __init__(self):
        self._handlers = []
        self._last_activity = time.ticks_ms()
        self._current_state = -1

    def add_handler(self, timeout_ms: int, enter_handler, exit_handler=None):
        self._handlers.append((int(timeout_ms), enter_handler, exit_handler))
        self._handlers.sort(key=lambda x: x[0])

    def remove_handler(self, index: int):
        if 0 <= index < len(self._handlers):
            del self._handlers[index]

    def clear_handlers(self):
        self._handlers = []
        self._current_state = -1

    def reset(self):
        current = int(self._current_state)
        if current != -1:
            if self._handlers[current][2]:
                self._handlers[current][2](self)
        self._last_activity = time.ticks_ms()
        self._current_state = -1

    def update(self) -> int:
        handlers = self._handlers
        if not handlers:
            return -1

        idle_time = self.idle_time
        new_state = int(-1)
        length = int(len(handlers))

        i = int(0)
        while i < length:
            if idle_time >= int(handlers[i][0]):
                new_state = i
            i += 1

        current = int(self._current_state)
        if new_state != current:
            if current != -1 and handlers[current][2]:
                handlers[current][2](self)
            self._current_state = new_state
            if new_state != -1:
                handlers[new_state][1](self)

        return int(self._current_state)

    @property
    def idle_time(self) -> int:
        return int(time.ticks_diff(time.ticks_ms(), self._last_activity))
