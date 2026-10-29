# frozen_string_literal: true

require "set"

# Works out the SEO fields for every page, used by _includes/seo.html:
#
#   seo_title        <title>, kept to 60 characters
#   seo_description  meta description, 70-160 characters, no ads/links/timestamps
#   seo_image        share image (absolute or site path)
#   seo_noindex      true for mock content and later feed pages' duplicates
#
# Front matter can override any of them (seo_title, description, image).
module CadeSeo
  TITLE_MAX = 60
  DESC_MIN = 70
  DESC_MAX = 160
  SUFFIX = " | CADE Media"

  # Lines that are sponsor reads, links, timestamps or contact boilerplate
  SKIP = /https?:\/\/|www\.|\[ad\]|sponsor|supporting|\bdeal\b|\bcode\b|discount|\S+@\S+|^\s*\(?\d{1,2}:\d{2}|whatsapp|voice note|patreon|subscribe|\bjoin the\b|po box|send (?:us|in)\b|\bmerch\b|ad ?choices|podcastchoices|nordvpn|this clip is a section from/i

  # What to add when a description is too short, by collection
  CONTEXT = {
    "videos" => "Watch on CADE Media, the YouTube channel for cycling culture for real people.",
    "podcasts" => "The Wild Ones, the weekly cycling podcast from CADE Media.",
    "tiktoks" => "A short clip from CADE Media on TikTok — cycling news, reviews and chat for real people.",
    "instagram" => "From CADE Media on Instagram — cycling culture for real people.",
    "posts" => "An update from CADE Media, cycling culture for real people.",
    "pages" => "CADE Media — cycling culture for real people."
  }.freeze

  # For long titles, where the full context wouldn't fit
  CONTEXT_SHORT = {
    "videos" => "A CADE Media video on YouTube.",
    "podcasts" => "The Wild Ones podcast from CADE Media.",
    "tiktoks" => "CADE Media on TikTok.",
    "instagram" => "CADE Media on Instagram.",
    "posts" => "An update from CADE Media.",
    "pages" => "CADE Media."
  }.freeze

  class Generator < Jekyll::Generator
    safe true
    priority :lowest # after the feed pages are generated

    def generate(site)
      @site = site
      @boilerplate = repeated_lines(site)
      docs = site.collections.values.flat_map(&:docs)
      (docs + site.pages).each { |item| apply(item) }
    end

    private

    def apply(item)
      data = item.data
      return if data["layout"].nil? || data["layout"] == "redirect" || !item.output_ext.to_s.end_with?(".html")

      collection = item.respond_to?(:collection) && item.collection ? item.collection.label : "pages"
      data["seo_title"] ||= title_for(item, collection)
      data["seo_description"] = description_for(item, collection)
      data["seo_image"] ||= image_for(item, collection)
      if data["mock"]
        data["seo_noindex"] = true
        data["sitemap"] = false
      end
    end

    # ---------- Titles ----------

    def title_for(item, collection)
      data = item.data
      base = data["title"].to_s.strip
      base = "#{base} · page #{data['pager']['page']}" if data["pager"] && data["pager"]["page"].to_i > 1
      base = "#{base} — CADE on TikTok" if collection == "tiktoks"
      base = "#{base} — CADE on Instagram" if collection == "instagram"
      return @site.config["title"] if base.empty?
      return base if base == @site.config["title"]
      return base + SUFFIX if (base + SUFFIX).length <= TITLE_MAX

      shorten(base, TITLE_MAX)
    end

    # ---------- Descriptions ----------

    def description_for(item, collection)
      data = item.data
      # Feed pages: one description per filter and page number
      return feed_description(data) if data["pager"]

      text = data["description"].to_s.strip
      text = data["intro"].to_s.strip if text.empty?
      # Only documents have prose bodies; a page's body is template code
      text = summary_from(item.content) if text.empty? && collection != "pages"
      text = clean(text)
      title = data["title"].to_s.strip
      text = clean("#{sentence(title)} #{text}") if text.length < DESC_MIN && !title.empty? && !text.include?(title)
      if text.length < 120 && (text.empty? || text.chomp(".") == title.chomp("."))
        # Nothing but the title to go on: add what and where it is
        long = clean("#{sentence(text)} #{CONTEXT.fetch(collection, CONTEXT['pages'])}")
        text = long.length <= DESC_MAX ? long : clean("#{sentence(text)} #{CONTEXT_SHORT.fetch(collection, CONTEXT_SHORT['pages'])}")
      end
      text = clean("#{sentence(text)} #{CONTEXT.fetch(collection, CONTEXT['pages'])}") if text.length < DESC_MIN
      text = @site.config["description"].to_s.strip if text.empty?
      text.length > DESC_MAX ? shorten(text, DESC_MAX) : text
    end

    FEED_TEXT = {
      "all" => "Every CADE Media video, Wild Ones podcast episode, clip and update in one timeline, newest first.",
      "video" => "Every CADE Media YouTube video — bike reviews, first looks, rides and the podcast on camera — newest first.",
      "podcast" => "Every episode of The Wild Ones, CADE Media's weekly cycling podcast on bike tech, news and life on two wheels.",
      "clip" => "Short clips from CADE Media on TikTok and YouTube — the best bits of the podcast and channel, newest first.",
      "instagram" => "Photos and posts from CADE Media on Instagram, from behind the scenes of cycling culture for real people.",
      "post" => "Updates from the CADE Media team on Bluesky — news, notes and what's coming next, newest first."
    }.freeze

    def feed_description(data)
      text = FEED_TEXT.fetch(data["filter"].to_s, FEED_TEXT["all"])
      page = data["pager"]["page"].to_i
      text = "#{text} Page #{page} of #{data['pager']['total_pages']}." if page > 1
      text.length > DESC_MAX ? shorten(text, DESC_MAX) : text
    end

    # First lines that read like a summary, up to about a description's length
    def summary_from(content)
      lines = content.to_s.gsub(/<[^>]+>/, " ").split(/\n+/).map { |l| strip_markdown(l) }
      good = lines.reject { |l| l.length < 20 || l.match?(SKIP) || @boilerplate.include?(l) }
      out = +""
      good.each do |line|
        break if out.length >= DESC_MIN
        out << " " unless out.empty?
        out << line
      end
      out
    end

    # A title as a sentence: add a full stop unless it already ends in punctuation
    def sentence(title)
      t = title.to_s.strip
      t.match?(/[.!?…]\z/) ? t : "#{t}."
    end

    def strip_markdown(line)
      line.gsub(/<(https?:[^>]+)>/, "").gsub(/!?\[([^\]]*)\]\([^)]*\)/, '\1').gsub(/\\([\\`*_\[\]<>|#])/, '\1')
          .gsub(/[*_`#>]+/, "").gsub(/\s+/, " ").strip
    end

    def clean(text)
      text.gsub(/https?:\/\/\S+/, "").gsub(/\s+/, " ").gsub(/\s+([.,!?])/, '\1').gsub(/\.\.+(?!\.)/, ".").strip
    end

    # Lines repeated across many items in a collection (sign-offs, sponsor reads)
    def repeated_lines(site)
      counts = Hash.new(0)
      site.collections.each_value do |c|
        c.docs.each { |d| d.content.to_s.split(/\n+/).map { |l| strip_markdown(l) }.uniq.each { |l| counts[l] += 1 } }
      end
      counts.select { |_, n| n >= 4 }.keys.to_set
    end

    # ---------- Images ----------

    def image_for(item, collection)
      data = item.data
      case collection
      when "videos" then "https://i.ytimg.com/vi/#{data['source_id']}/maxresdefault.jpg"
      when "podcasts" then data["image"] || "/assets/images/wild-ones-podcast.jpg"
      when "tiktoks", "instagram" then data["thumbnail"]
      else data["image"] || "/assets/images/og-default.jpg"
      end
    end

    # Cut at a word boundary and add an ellipsis
    def shorten(text, max)
      cut = text[0, max - 1]
      cut = cut[0, cut.rindex(" ")] if cut.rindex(" ") && cut.rindex(" ") > max / 2
      cut.sub(/[\s,;:\-–—·|+]+\z/, "") + "…"
    end
  end
end
