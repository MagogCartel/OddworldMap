// The exporter's oracle, linked against relive_api itself so the reference
// implementation judges our JSON. `check` runs a document through the reader
// that ImportPathJsonToBinary runs first — every required key, every property,
// every enum label — with no LVL involved; `enum` and `export` are for the disc
// session, when a real LVL is on hand to diff against. Built by
// tools/relive_verify.py.

// relive_api.hpp first: ApiContext.hpp needs the Types.hpp it pulls in
#include "relive_api.hpp"
#include "JsonMapRootInfoReader.hpp"
#include "JsonReaderAO.hpp"
#include "JsonReaderAE.hpp"
#include "file_api.hpp"
#include "../../AliveLibCommon/logger.hpp"

#include <cstdio>
#include <string>
#include <typeinfo>

INITIALIZE_EASYLOGGINGPP

static int checkOne(const std::string& fileName)
{
    // named and flushed first: a missing numeric property is a jsonxx
    // assert-abort, not an exception, and the abort should name its file
    std::printf("checking %s\n", fileName.c_str());
    std::fflush(stdout);
    ReliveAPI::FileIO fileIO;
    try
    {
        ReliveAPI::JsonMapRootInfoReader rootInfo;
        rootInfo.Read(fileIO, fileName);
        if (rootInfo.mMapRootInfo.mVersion != ReliveAPI::GetApiVersion())
        {
            std::printf("FAIL %s: api_version %d != %d\n", fileName.c_str(),
                        rootInfo.mMapRootInfo.mVersion, ReliveAPI::GetApiVersion());
            return 1;
        }
        ReliveAPI::Context context;
        std::size_t cameras = 0, objects = 0, collisions = 0;
        if (rootInfo.mMapRootInfo.mGame == "AO")
        {
            ReliveAPI::JsonReaderAO reader;
            const auto loaded = reader.Load(fileIO, fileName, context);
            cameras = loaded.mPerCamData.size();
            collisions = loaded.mCollisions.size();
            for (const auto& cam : loaded.mPerCamData)
            {
                objects += cam.mTlvBlobs.size();
            }
        }
        else
        {
            ReliveAPI::JsonReaderAE reader;
            const auto loaded = reader.Load(fileIO, fileName, context);
            cameras = loaded.mPerCamData.size();
            collisions = loaded.mCollisions.size();
            for (const auto& cam : loaded.mPerCamData)
            {
                objects += cam.mTlvBlobs.size();
            }
        }
        for (const auto& r : context.RemappedEnumValues())
        {
            std::printf("FAIL %s: enum %s value %s silently remapped to %s\n", fileName.c_str(),
                        r.mEnumTypeName.c_str(), r.mEnumValueInJson.c_str(), r.mValueUsed.c_str());
        }
        if (!context.Ok() || !context.RemappedEnumValues().empty())
        {
            return 1;
        }
        std::printf("OK %s cameras=%zu objects=%zu collisions=%zu\n", fileName.c_str(),
                    cameras, objects, collisions);
        return 0;
    }
    catch (const ReliveAPI::Exception& e)
    {
        std::printf("FAIL %s: %s\n", fileName.c_str(), typeid(e).name());
        return 1;
    }
    catch (const std::exception& e)
    {
        std::printf("FAIL %s: %s\n", fileName.c_str(), e.what());
        return 1;
    }
}

int main(int argc, char** argv)
{
    const std::string mode = argc > 1 ? argv[1] : "";
    ReliveAPI::FileIO fileIO;
    if (mode == "check" && argc > 2)
    {
        int failures = 0;
        for (int i = 2; i < argc; i++)
        {
            failures += checkOne(argv[i]);
        }
        return failures ? 1 : 0;
    }
    if (mode == "enum" && argc == 3)
    {
        const auto result = ReliveAPI::EnumeratePaths(fileIO, argv[2]);
        std::printf("%s:", result.pathBndName.c_str());
        for (const auto id : result.paths)
        {
            std::printf(" %d", id);
        }
        std::printf("\n");
        return 0;
    }
    if (mode == "export" && argc == 5)
    {
        ReliveAPI::Context context;
        ReliveAPI::ExportPathBinaryToJson(fileIO, argv[4], argv[2], std::atoi(argv[3]), context);
        std::printf("%s %s\n", context.Ok() ? "OK" : "context not ok:", argv[4]);
        return context.Ok() ? 0 : 1;
    }
    std::printf("usage: relive_check check <json>...\n"
                "       relive_check enum <lvl>\n"
                "       relive_check export <lvl> <path_id> <out.json>\n");
    return 2;
}
