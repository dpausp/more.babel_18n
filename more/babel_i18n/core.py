# -*- coding: utf-8 -*-
"""
    more.babel_i18n.babel
    ~~~~~~~~~~~~~~~~~~~~~

    The actual Flask extension.

    :copyright:
        (c) 2017 by Tobias dpausp
        (c) 2013 by Armin Ronacher, Daniel Neuhäuser and contributors.
    :license: BSD, see LICENSE for more details.
"""
import os
from babel import Locale
import morepath
from more.babel_i18n.domain import Domain
try:
    from pytz.gae import pytz
except ImportError:
    from pytz import timezone
else:
    timezone = pytz.timezone  # pragma: no cover

from .constants import DEFAULT_LOCALE, DEFAULT_TIMEZONE,\
    DEFAULT_DATE_FORMATS


class BabelApp(morepath.App):
    """Central controller class that can be used to configure how
    Flask-Babel behaves.  Each application that wants to use Flask-Babel
    has to create, or run :meth:`init_app` on, an instance of this class
    after the configuration was initialized.
    """

    def babel_init(self):
        """Initializes the more.babel_i18n App.
        """
        cfg = self.settings.babel_i18n
        #: a mapping of Babel datetime format strings that can be modified
        #: to change the defaults.  If you invoke :func:`format_datetime`
        #: and do not provide any format string Flask-Babel will do the
        #: following things:
        #:
        #: 1.   look up ``date_formats['datetime']``.  By default ``'medium'``
        #:      is returned to enforce medium length datetime formats.
        #: 2.   ``date_formats['datetime.medium'] (if ``'medium'`` was
        #:      returned in step one) is looked up.  If the return value
        #:      is anything but `None` this is used as new format string.
        #:      otherwise the default for that language is used.
        self.babel = BabelI18n(self, domain=cfg.domain, date_formats=DEFAULT_DATE_FORMATS.copy())

        if cfg.configure_jinja:
            self.jinja_env.filters.update(
                datetimeformat=format_datetime,
                dateformat=format_date,
                timeformat=format_time,
                timedeltaformat=format_timedelta,

                numberformat=format_number,
                decimalformat=format_decimal,
                currencyformat=format_currency,
                percentformat=format_percent,
                scientificformat=format_scientific,
            )
            self.jinja_env.add_extension('jinja2.ext.i18n')
            self.jinja_env.install_gettext_callables(
                lambda x: get_domain().get_translations().ugettext(x),
                lambda s, p, n: get_domain().get_translations()
                                            .ungettext(s, p, n),
                newstyle=True
            )


class BabelI18n:
    def __init__(self, app, domain, date_formats):
        self.app = app
        self.settings = self.app.settings.babel_i18n
        self.domain = domain
        self.date_formats = date_formats
        self.locale_selector_func = None
        self.timezone_selector_func = None
        self.locale_cache = {}

    def localeselector(self, f):
        """Registers a callback function for locale selection.  The default
        behaves as if a function was registered that returns `None` all the
        time.  If `None` is returned, the locale falls back to the one from
        the configuration.

        This has to return the locale as string (eg: ``'de_AT'``, ''`en_US`'')
        """
        self.locale_selector_func = f
        return f

    def timezoneselector(self, f):
        """Registers a callback function for timezone selection.  The default
        behaves as if a function was registered that returns `None` all the
        time.  If `None` is returned, the timezone falls back to the one from
        the configuration.

        This has to return the timezone as string (eg: ``'Europe/Vienna'``)
        """
        self.timezone_selector_func = f
        return f

    def list_translations(self):
        """Returns a list of all the locales translations exist for.  The
        list returned will be filled with actual locale objects and not just
        strings.

        .. versionadded:: 0.6
        """

        # XXX: Wouldn't it be better to list the locales from the domain?
        dirname = os.path.join(self.app.root_path, 'translations')
        if not os.path.isdir(dirname):
            return []
        result = []
        for folder in os.listdir(dirname):
            locale_dir = os.path.join(dirname, folder, 'LC_MESSAGES')
            if not os.path.isdir(locale_dir):
                continue
            if filter(lambda x: x.endswith('.mo'), os.listdir(locale_dir)):
                result.append(Locale.parse(folder))
        if not result:
            result.append(Locale.parse(self.default_locale))
        return result

    @property
    def default_locale(self):
        """The default locale from the configuration as instance of a
        `babel.Locale` object.
        """
        return self.load_locale(self.settings.default_locale)

    @property
    def default_timezone(self):
        """The default timezone from the configuration as instance of a
        `pytz.timezone` object.
        """
        return timezone(self.settings.default_timezone)

    def load_locale(self, locale):
        """Load locale by name and cache it. Returns instance of a
        `babel.Locale` object.
        """
        rv = self.locale_cache.get(locale)
        if rv is None:
            self.locale_cache[locale] = rv = Locale.parse(locale)
        return rv

    def __repr__(self):
        return '<BabelI18n({}, {})>'.format(self.babel, self.domain)


@BabelApp.setting_section(section="babel_i18n")
def babel_i18n_settings():
    return {
        'default_locale': DEFAULT_LOCALE,
        'default_timezone': DEFAULT_TIMEZONE,
        'configure_jinja': True,
        'domain': Domain()
    }