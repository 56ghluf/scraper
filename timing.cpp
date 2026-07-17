#include "timing.h"

#include <chrono>

// ***Timer class***
Timer::Timer()
  : start_(Clock::now()) {}

void Timer::operator()() {
  start_ = Clock::now();
}

double Timer::elapsed() const {
  return std::chrono::duration<double, std::ratio<60>>(Clock::now() - start_).count();
}
