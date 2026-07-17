#pragma once

#include <chrono>
#include <ostream>
#include <string>

namespace chr = std::chrono;

class DateInterval {
public:
  DateInterval(const chr::year_month_day & = chr::year{2000} / 1 / 1,
               const chr::days & = chr::days{10});

  explicit operator bool();

  DateInterval &operator++();

  const chr::year_month_day &interval_start() const;
  const chr::year_month_day &interval_end() const;

private:
  chr::year_month_day interval_start_;
  chr::year_month_day interval_end_;

  const chr::days delta_;

  const chr::year_month_day end_date_;
};

std::ostream &operator<<(std::ostream &, const DateInterval &);

// 07%2F14%2F2022+-+07%2F15%2F2022

std::string date_to_string(const chr::year_month_day &,
                           const std::string & = "%2F");
