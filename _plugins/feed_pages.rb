# frozen_string_literal: true

# Builds the paginated feed timeline:
#   /feed/            /feed/page/2/ …     everything, newest first
#   /feed/<type>/     /feed/<type>/page/2/ …  one per filter in _config.yml
#
# Items are blog posts plus every document in the content collections. Each
# page gets `page.items` and `page.pager` (page, total_pages, prev/next urls).
module CadeFeed
  COLLECTIONS = %w[videos podcasts tiktoks instagram].freeze

  class FeedPage < Jekyll::Page
    def initialize(site, dir, items, pager, filter)
      @site = site
      @base = site.source
      @dir = dir
      @name = "index.html"
      process(@name)
      self.content = ""
      self.data = {
        "layout" => "feed",
        "title" => filter ? "#{filter['label']} · The Feed" : "The Feed",
        "description" => "Every video, podcast episode, clip, Instagram post and update from CADE Media, newest first.",
        "items" => items,
        "pager" => pager,
        "filter" => filter ? filter["key"] : "all",
        "sitemap" => pager["page"] == 1
      }
    end
  end

  class Generator < Jekyll::Generator
    safe true
    priority :low

    def generate(site)
      config = site.config["feed_pages"] || {}
      per_page = (config["per_page"] || 20).to_i
      items = site.posts.docs.dup
      COLLECTIONS.each { |name| items.concat(site.collections[name]&.docs || []) }
      items.sort_by! { |doc| doc.date }.reverse!

      # Shared with the sidebar: how many items of each type there are
      site.config["feed_counts"] = items.group_by { |d| d.data["type"] }.transform_values(&:size)
      site.config["feed_counts"]["all"] = items.size

      @sponsors = active_sponsors(site)
      @sponsor_position = (config["sponsor_position"] || 3).to_i

      paginate(site, "feed", items, per_page, nil)
      (config["filters"] || []).each do |filter|
        subset = items.select { |doc| doc.data["type"] == filter["key"] }
        paginate(site, "feed/#{filter['key']}", subset, per_page, filter)
      end
    end

    private

    # Sponsors whose start..end window includes the build date. The site is
    # rebuilt daily (deploy-pages.yml) so windows open and close on time.
    def active_sponsors(site)
      today = site.time.to_date
      (site.collections["sponsors"]&.docs || []).select do |doc|
        start = to_date(doc.data["start"])
        finish = to_date(doc.data["end"])
        (start.nil? || start <= today) && (finish.nil? || today <= finish)
      end.sort_by { |doc| to_date(doc.data["start"]) || Date.new(2000) }
    end

    def to_date(value)
      return nil if value.nil? || value.to_s.empty?
      return value.to_date if value.respond_to?(:to_date)
      Date.parse(value.to_s)
    end

    # Puts a sponsor at the configured position (3rd by default), rotating
    # through active sponsors page by page.
    def with_sponsor(slice, page_number)
      return slice if @sponsors.empty? || slice.empty?
      sponsor = @sponsors[(page_number - 1) % @sponsors.size]
      at = [@sponsor_position - 1, slice.size].min
      slice.dup.insert(at, sponsor)
    end

    def paginate(site, base, items, per_page, filter)
      total = [(items.size.to_f / per_page).ceil, 1].max
      (1..total).each do |n|
        dir = n == 1 ? base : "#{base}/page/#{n}"
        pager = {
          "page" => n,
          "total_pages" => total,
          "total_items" => items.size,
          "prev_url" => n > 1 ? url_for(base, n - 1) : nil,
          "next_url" => n < total ? url_for(base, n + 1) : nil,
          "first_url" => url_for(base, 1)
        }
        slice = items.slice((n - 1) * per_page, per_page) || []
        site.pages << FeedPage.new(site, dir, with_sponsor(slice, n), pager, filter)
      end
    end

    def url_for(base, n)
      n == 1 ? "/#{base}/" : "/#{base}/page/#{n}/"
    end
  end
end
