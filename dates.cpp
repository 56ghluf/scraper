#include "dates.h"

#include <chrono>
#include <format>
#include <ostream>
#include <string>

DateInterval::DateInterval(const chr::year_month_day &start,
                           const chr::days &delta)
    : interval_start_{start},
      interval_end_{chr::sys_days{start} + delta - chr::days{1}}, delta_{delta},
      end_date_{std::chrono::floor<std::chrono::days>(
          std::chrono::system_clock::now())} {};

// No resets for dates, as designed to be used in a for loop once
DateInterval::operator bool() {
  if (end_date_ < interval_start_)
    return false;
  return true;
}

DateInterval &DateInterval::operator++() {
  if (*this) {
    interval_start_ = chr::sys_days{interval_start_} + delta_;
    interval_end_ = chr::sys_days{interval_end_} + delta_;

    if (interval_end_ > end_date_)
      interval_end_ = end_date_;
  }

  return *this;
}

const chr::year_month_day &DateInterval::interval_start() const {
  return interval_start_;
}

const chr::year_month_day &DateInterval::interval_end() const {
  return interval_end_;
}

std::ostream &operator<<(std::ostream &ost, const DateInterval &di) {
  return ost << "interval start: " << di.interval_start()
             << " | interval end: " << di.interval_end();
}

std::string date_to_string(const chr::year_month_day &date,
                           const std::string &sep) {
  return std::format("{:02}{}{:02}{}{:04}", static_cast<unsigned>(date.month()),
                     sep, static_cast<unsigned>(date.day()), sep,
                     static_cast<int>(date.year()));
}
