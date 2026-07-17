#include <chrono>
#include <cstdlib>
#include <iostream>
#include <fstream>
#include <thread>

#include <cpr/cpr.h>

#include "dates.h"
#include "search_result_parsing.h"
#include "timing.h"

int main() {
  std::ofstream out_file("data.csv");

  if (out_file.fail()) {
    std::cerr << "main: failed to open data.csv, aborting\n";
    return EXIT_FAILURE;
  }

  std::string base_url{
      "http://openinsider.com/"
      "screener?s=&o=&pl=&ph=&ll=&lh=&fd=0&fdr=&td=-1&tdr={}+-+{}"
      "&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&"
      "sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&"
      "oc2h=&sortcol=0&cnt=1000&page=1"};

  bool first{true};

  std::cout << "starting scraping\n\n";
  Timer t;

  for (DateInterval di; di; ++di) {
    const std::string start_date{date_to_string(di.interval_start())};
    const std::string end_date{date_to_string(di.interval_end())};
    const std::string url{
        std::vformat(base_url, std::make_format_args(start_date, end_date))};

    const cpr::Response r{cpr::Get(
        cpr::Url{url},
        cpr::Header{
            {"User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) Gecko/20100101 Firefox/152.0"},
            {"Accept",
             "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            {"Accept-Language", "en-US,en;q=0.9"},
            {"Accept-Encoding", "gzip, deflate"},
            {"Connection", "keep-alive"}})};

    parse_table(r.text, out_file, first);

    if (first)
      first = false;

    std::this_thread::sleep_for(std::chrono::seconds{1});
    std::cout << "completed interval " << di << '\n';
  }

  const double dt{t.elapsed()};

  const unsigned int mins{static_cast<unsigned int>(dt)};
  const unsigned int secs{
      static_cast<unsigned int>((dt - static_cast<double>(mins)) * 60)};

  std::cout << "\nfinished, took " << mins << " minutes " << secs
            << " seconds\n";

  out_file.close();

  return EXIT_SUCCESS;
}
