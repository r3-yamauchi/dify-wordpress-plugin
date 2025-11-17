# where: wordpress/main.py
# what: Defines the entrypoint for the wordpress tool plugin.
# why: Dify launches this module to expose the registered tools during runtime.

from dify_plugin import Plugin, DifyPluginEnv

plugin = Plugin(DifyPluginEnv(MAX_REQUEST_TIMEOUT=300))

if __name__ == '__main__':
    plugin.run()
