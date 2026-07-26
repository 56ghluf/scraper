#include <fstream>
#include  <iostream>
#include <format>

#include <cpr/cpr.h>

#include "dates.h"
#include "search_result_parsing.h"

int main() {
  std::ofstream out_file("curr_data/raw_data.csv");

  if (out_file.fail()) {
    std::cerr << "main: failed to open curr_data/raw_data.csv, aborting\n";
    return EXIT_FAILURE;
  }

  const std::string base_url{
      "http://openinsider.com/"
      "screener?s=&o=&pl=&ph=&ll=&lh=&fd=-1&fdr={}+-+{}&td=0&tdr=&fdlyl=&fdlyh="
      "&daysago=&xp=1&xs=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&"
      "nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=1000&"
      "page=1"};

  const auto [start_date, end_date] = curr_dates();

  const std::string url{
      std::vformat(base_url, std::make_format_args(start_date, end_date))};

  const cpr::Response r{cpr::Get(
      cpr::Url{url},
      cpr::Header{
          {"User-Agent", "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:152.0) "
                         "Gecko/20100101 Firefox/152.0"},
          {"Accept",
           "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
          {"Accept-Language", "en-US,en;q=0.9"},
          {"Accept-Encoding", "gzip, deflate"},
          {"Connection", "keep-alive"}})};

  parse_table(r.text, out_file, true);
}
