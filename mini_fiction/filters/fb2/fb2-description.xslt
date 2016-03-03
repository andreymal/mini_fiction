<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:date="http://exslt.org/dates-and-times"
    extension-element-prefixes="date">
    
    <xsl:param name="genre" select="'entertainment'"/>
    <xsl:param name="author_name" select="'Anonymous'"/>
    <xsl:param name="title" select="''"/>
    <xsl:param name="doc_id" select="''"/>
    <xsl:param name="language" select="'ru'"/>
    <xsl:param name="date" select="date:date-time()"/>
    <xsl:param name="date_string" select="''"/>
    <xsl:param name="picture_b64encoded_data" select="''"/>
    
<xsl:template name="create-fb2-description">
    <xsl:param name="annotation"/>

    <description>
        <title-info>
            <genre><xsl:value-of select="$genre"/></genre>
            <author>
                <first-name><xsl:value-of select="$author_name"/></first-name>
                <middle-name/>
                <last-name/>
            </author>
            <book-title><xsl:value-of select="$title"/></book-title>
            <xsl:if test="$annotation">
                <annotation>
                    <xsl:copy-of select="$annotation"/>
                </annotation>
            </xsl:if>
            <xsl:if test="$picture_b64encoded_data">
                <coverpage>
                    <image xlink:href="#cover.jpg"/>
                </coverpage>
            </xsl:if>
            <lang><xsl:value-of select="$language"/></lang>
        </title-info>
        <document-info>
            <author>
                <first-name><xsl:value-of select="$author_name"/></first-name>
                <middle-name/>
                <last-name/>
            </author>
            <date value="{substring-before($date, 'T')}">
                <xsl:choose>
                    <xsl:when test="not($date_string)">
                        <xsl:value-of select="$date"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:value-of select="$date_string"/>
                    </xsl:otherwise>
                </xsl:choose>
            </date>
            <id><xsl:value-of select="$doc_id"/></id>
            <version>2.0</version>
        </document-info>
    </description>
</xsl:template>

<xsl:template name="create-fb2-footer">
    <xsl:if test="$picture_b64encoded_data">
        <binary id="cover.jpg" content-type="image/jpeg">
            <xsl:value-of select="$picture_b64encoded_data"/>
        </binary>
    </xsl:if>
</xsl:template>
    
</xsl:stylesheet>