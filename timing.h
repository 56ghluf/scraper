#include <chrono>

typedef std::chrono::high_resolution_clock Clock;

// ***Timer class***
class Timer {
public:
  Timer();

  void operator()();

  double elapsed() const;

private:
  std::chrono::time_point<Clock> start_;
};
